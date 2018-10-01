from flask import current_app, request, Blueprint
from flask.ext.discoverer import advertise
from .models import User, Profile
from datetime import datetime
from dateutil import parser
from sqlalchemy import exc, and_
from sqlalchemy.orm import load_only
import json
import logging

bp = Blueprint('orcid', __name__)

@advertise(scopes=[], rate_limit = [100, 3600*24])
@bp.route('/exchangeOAuthCode', methods=['GET'])
def get_access_token():
    '''Exchange 'code' for 'access_token' data'''
    payload = dict(request.args)
    if 'code' not in payload:
        raise Exception('Parameter code is missing')
    headers = {'Accept': 'application/json'}
    data = {
      'client_id': current_app.config['ORCID_CLIENT_ID'],
      'client_secret': current_app.config['ORCID_CLIENT_SECRET'],
      'code': payload['code'][0],
      'grant_type': 'authorization_code'
    }
    #print current_app.config['ORCID_OAUTH_ENDPOINT'], data, headers
    r = current_app.client.post(current_app.config['ORCID_OAUTH_ENDPOINT'], data=data, headers=headers)
    if r.status_code != 200:
        logging.error('For ORCID code {}, there was an error getting the token from the ORCID API.'.
                      format(payload['code'][0]))

    # update/create user account
    data = r.json()
    if 'orcid' in data:
        with current_app.session_scope() as session:
            u = session.query(User).filter_by(orcid_id=data['orcid']).options(load_only(User.orcid_id)).first()
            p = session.query(Profile).filter_by(orcid_id=data['orcid']).options(load_only(Profile.orcid_id)).first()
            if not u:
                u = User(orcid_id=data['orcid'], created=datetime.utcnow())
            if not p:
                p = Profile(orcid_id=data['orcid'], created=datetime.utcnow())
            u.updated = datetime.utcnow()
            p. updated = datetime.utcnow()
            u.access_token = data['access_token']
            # save the user
            session.begin_nested()
            try:
                session.add(u)
                session.add(p)
                session.commit()
            except exc.IntegrityError as e:
                session.rollback()
            # per PEP-0249 a transaction is always in progress
            session.commit()

    return r.text, r.status_code


@advertise(scopes=[], rate_limit = [1000, 3600*24])
@bp.route('/<orcid_id>/orcid-profile', methods=['GET', 'POST'])
def orcid_profile(orcid_id):
    '''Get/Set /[orcid-id]/orcid-profile - all communication exclusively in JSON'''
    payload, headers = check_request(request)
    if request.method == 'GET':
        r = current_app.client.get(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/record',
                         headers=headers)
    else:
        r = current_app.client.post(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/record',
                         json=payload, headers=headers)

    # save the profile data (just in case the user revokes access_token, we can still get the update
    # from our local data); however - normally the updater should grab the latest data from orcid
    if r.status_code == 200:
        update_profile(orcid_id, r.text)

    return r.text, r.status_code

@advertise(scopes=[], rate_limit=[1000, 3600 * 24])
@bp.route('/<orcid_id>/orcid-profile/<type>', methods=['GET'])
def orcid_profile_local(orcid_id, type):
    '''Get /[orcid-id]/orcid-profile/<simple,full> - returns either bibcodes and statuses (/simple) or all
    records and saved metadata (/full) - all communication exclusively in JSON'''

    payload, headers = check_request(request)
    update = request.args.get('update', False)
    if type not in ['simple','full']:
        return json.dumps('Endpoint /orcid-profile/%s does not exist'.format(type)), 404

    r = current_app.client.get(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/record',
                                   headers=headers)

    if r.status_code == 200:
        update_profile_local(orcid_id, data=r.text, force=update)
    else:
        logging.warning('Failed fetching fresh profile from ORCID for %s'.format(orcid_id))

    with current_app.session_scope() as session:
        profile = session.query(Profile).filter_by(orcid_id=orcid_id).first()
        if type == 'simple':
            bibcodes, statuses = profile.get_bibcodes()
            records = dict(zip(bibcodes, statuses))
        elif type == 'full':
            records = profile.get_records()

    return json.dumps(records), 200

@advertise(scopes=[], rate_limit = [1000, 3600*24])
@bp.route('/<orcid_id>/orcid-works/<putcode>', methods=['GET', 'PUT', 'DELETE'])
def orcid_works(orcid_id,putcode):
    '''Get/Set /[orcid-id]/orcid-works - all communication exclusively in JSON'''

    payload, headers = check_request(request)

    if request.method == 'GET':
        if ',' in putcode:
            r = current_app.client.get(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/works/' + putcode,
                             headers=headers)
        else:
            r = current_app.client.get(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/work/' + putcode,
                          headers=headers)
    elif request.method == 'PUT':
        r = current_app.client.put(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/work/' + putcode,
                      json=payload, headers=headers)
        update_profile(orcid_id)
    elif request.method == 'DELETE':
        r = current_app.client.delete(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/work/' + putcode,
                      headers=headers)
        update_profile(orcid_id)

    return r.text, r.status_code


@advertise(scopes=[], rate_limit=[1000, 3600 * 24])
@bp.route('/<orcid_id>/orcid-work', methods=['POST'])
def orcid_work_add_single(orcid_id):
    '''Get/Set /[orcid-id]/orcid-works - all communication exclusively in JSON'''

    payload, headers = check_request(request)

    r = current_app.client.post(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/work',
                        json=payload, headers=headers)
    update_profile(orcid_id)

    return r.text, r.status_code

@advertise(scopes=[], rate_limit=[1000, 3600 * 24])
@bp.route('/<orcid_id>/orcid-works', methods=['POST'])
def orcid_work_add_multiple(orcid_id):
    '''Get/Set /[orcid-id]/orcid-works - all communication exclusively in JSON'''

    payload, headers = check_request(request)

    r = current_app.client.post(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/works',
                        json=payload, headers=headers)
    update_profile(orcid_id)

    return r.text, r.status_code

@advertise(scopes=['ads-consumer:orcid'], rate_limit = [1000, 3600*24])
@bp.route('/export/<iso_datestring>', methods=['GET'])
def export(iso_datestring):
    '''Get the latest changes (as recorded in the ORCID)
    The optional argument latest_point is RFC3339, ie. '2008-09-03T20:56:35.450686Z'
    '''

    latest_point = parser.parse(iso_datestring) # RFC 3339 format

    payload = dict(request.args)
    allowed_fields = ['orcid_id', 'created', 'updated', 'profile']
    fields = payload.get('fields', allowed_fields)
    fields_to_load = list(set(fields) & set(allowed_fields))

    if len(fields_to_load) == 0:
        return json.dumps({'error': 'Wrong input values for fields: %s' % payload.get('fields')}), 404

    # poorman's version of paging, but it works because the time resolution is in
    # microseconds
    output = []
    with current_app.session_scope() as session:
        recs = session.query(User).filter(User.updated >= latest_point) \
            .order_by(User.updated.asc()) \
            .limit(current_app.config.get('MAX_PROFILES_RETURNED', 10)) \
            .options(load_only(*fields_to_load)) \
            .all()

        for r in recs:
            o = {}
            for k in fields_to_load:
                v = getattr(r, k)
                if k == 'profile':
                    try:
                        v = json.loads(unicode(v))
                    except:
                        v = None
                if hasattr(v, 'isoformat'):
                    v = v.isoformat()
                o[k] = v
            output.append(o)

    return json.dumps(output), 200


@advertise(scopes=['ads-consumer:orcid'], rate_limit = [1000, 3600*24])
@bp.route('/get-profile/<orcid_id>', methods=['GET'])
def get_profile(orcid_id):
    '''Fetches the latest orcid-profile'''
    with current_app.session_scope() as session:
        u = session.query(User).filter_by(orcid_id=orcid_id).first()
        if not u:
            return json.dumps({'error': 'We do not have a record for: %s' % orcid_id}), 404

        if not u.access_token:
            return json.dumps({'error': 'We do not have access_token for: %s' % orcid_id}), 404

        out = u.toJSON()

        payload = dict(request.args)
        if payload.get('reload', False):
            h = {
                 'Accept': 'application/json',
                 'Authorization': 'Bearer %s' % u.access_token,
                 'Content-Type': 'application/json'
                 }

            r = current_app.client.get(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/record',
                             headers=h)
            if r.status_code == 200:
                # update our record (but avoid setting the updated date)
                j = r.json()
                session.begin_nested()
                try:
                    u.profile = json.dumps(j)
                    session.add(u)
                    session.commit()
                    out['profile'] = j
                except exc.IntegrityError as e:
                    session.rollback()
                # per PEP-0249 a transaction is always in progress
                session.commit()
            else:
                raise Exception('Orcid API returned err code (refreshing profile)')

    return json.dumps(out), 200


@advertise(scopes=[], rate_limit = [100, 3600*24])
@bp.route('/preferences/<orcid_id>', methods=['GET', 'POST'])
def preferences(orcid_id):
    '''Allows you to store/retrieve JSON data on the server side.
    It is always associated with the ORCID access token so there
    is no need for scope access
    '''

    # get the query data
    try:
        payload, headers = check_request(request)
    except Exception as e:
        return json.dumps({'msg': e.message or e.description}), 400

    access_token = headers['Authorization'][7:] # remove the 'Bearer:' thing

    if request.method == 'GET':
        with current_app.session_scope() as session:
            u = session.query(User).filter(and_(User.orcid_id==orcid_id, User.access_token==access_token)).options(load_only(User.orcid_id)).first()
            if not u:
                return '{}', 404 # not found
            return u.info or '{}', 200
    elif request.method == 'POST':
        d = json.dumps(payload)
        if len(d) > current_app.config.get('MAX_ALLOWED_JSON_SIZE', 1000):
            return json.dumps({'msg': 'You have exceeded the allowed storage limit, no data was saved'}), 400
        with current_app.session_scope() as session:
            u = session.query(User).filter(and_(User.orcid_id==orcid_id, User.access_token==access_token)).options(load_only(User.orcid_id)).first()
            if not u:
                return json.dumps({'error': 'We do not have a record for: %s' % orcid_id}), 404

            u.info = d

            session.begin_nested()
            try:
                session.merge(u)
                session.commit()
            except exc.IntegrityError:
                session.rollback()
                return json.dumps({'msg': 'We have hit a db error! The world is crumbling all around... (eh, btw, your data was not saved)'}), 500

            # per PEP-0249 a transaction is always in progress
            session.commit()
        return d, 200

@advertise(scopes=['ads-consumer:orcid'], rate_limit = [100, 3600*24])
@bp.route('/update-status/<orcid_id>', methods=['GET', 'POST'])
def update_status(orcid_id):
    """Gets/sets bibcode statuses for a given ORCID ID"""

    payload, headers = check_request(request)

    if request.method == 'GET':
        with current_app.session_scope() as session:
            profile = session.query(Profile).filter_by(orcid_id=orcid_id).first()
            recs = profile.get_records()
            statuses = profile.get_nested(recs,'status')
            records = dict(zip(recs, statuses))

        return json.dumps(records), 200

    if request.method == 'POST':
        if 'bibcodes' not in payload:
            raise Exception('Bibcodes are missing')
        if 'status' not in payload:
            raise Exception('Status is missing')
        with current_app.session_scope() as session:
            profile = session.query(Profile).filter_by(orcid_id=orcid_id).first()
            if type(payload['bibcodes']) != list:
                bibcodes = [payload['bibcodes']]
            else:
                bibcodes = payload['bibcodes']
            profile.update_status(bibcodes,payload['status'])
            good_bibc, good_statuses = profile.get_status(bibcodes)
            records = dict(zip(good_bibc, good_statuses))

        return json.dumps(records), 200

@advertise(scopes=[], rate_limit = [100, 3600*24])
@bp.route('/orcid-name/<orcid_id>', methods=['GET'])
def orcid_name(orcid_id):
    '''Get name from ORCID profile'''

    payload, headers = check_request(request)

    r = current_app.client.get(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/personal-details',
                                   headers=headers)

    return r.text, r.status_code


def update_profile(orcid_id, data=None):
    """Inserts data into the user record and updates the 'updated'
    column with the most recent timestamp"""

    with current_app.session_scope() as session:
        u = session.query(User).filter_by(orcid_id=orcid_id).options(load_only(User.orcid_id)).first()
        if u:
            u.updated = datetime.utcnow()
            if data:
                try:
                    #verify the data is a valid JSON
                    u.profile = json.dumps(json.loads(data))
                except:
                    logging.error('Invalid data passed in for {} (ignoring it)'.format(orcid_id))
                    logging.error(data)
            # save the user
            session.begin_nested()
            try:
                session.add(u)
                session.commit()
            except exc.IntegrityError as e:
                session.rollback()
            # per PEP-0249 a transaction is always in progress
            session.commit()

def update_profile_local(orcid_id, data=None, force=False):
    """Update local db with ORCID profile"""

    data = json.loads(data)

    with current_app.session_scope() as session:
        profile = session.query(Profile).filter_by(orcid_id=orcid_id).first()
        if not profile:
            logging.error('ORCID profile {} does not exist; creating'.format(orcid_id))
            profile = Profile(orcid_id=orcid_id, created=datetime.utcnow())
            force = True
        # data assumed to come from ORCID API /works endpoint
        if data:
            # convert milliseconds since epoch to seconds since epoch
            last_modified = data['activities-summary']['last-modified-date']['value']
            last_modified /= 1000.
            if force or (profile.updated < datetime.fromtimestamp(last_modified)):
                works = data['activities-summary']['works']['group']
                new_recs = {}
                update_recs = {}
                orcid_recs = []
                try:
                    current_recs = profile.bibcode.keys()
                except:
                    current_recs = []
                for work in works:
                    try:
                        id0, rec = find_record(work)
                    except:
                        continue
                    if id0 not in current_recs:
                        new_recs.update(rec)
                    else:
                        # if bibcode already in the profile, keep its status
                        rec[id0]['status'] = profile.bibcode[id0]['status']
                        update_recs.update(rec)
                    orcid_recs.append(id0)
                profile.add_records(new_recs)
                profile.add_records(update_recs)
                # remove records from the profile that aren't in the ORCID set
                remove_recs = list(set(current_recs)-set(orcid_recs))
                profile.remove_bibcodes(remove_recs)

        profile.updated = datetime.utcnow()
        # save the user
        session.begin_nested()
        try:
            session.add(profile)
            session.commit()
        except exc.IntegrityError as e:
            session.rollback()
            logging.warning('ORCID profile database error - updated bibcodes for %s were not saved.'.format(orcid_id))

def check_request(request):

    headers = dict(request.headers)
    if 'Orcid-Authorization' not in headers:
        raise Exception('Header Orcid-Authorization is missing')
    h = {
         'Accept': 'application/json',
         'Authorization': headers['Orcid-Authorization'],
         'Content-Type': 'application/json'
         }
    # transfer headers from the original
    #for x in ['Content-Type']:
    #    if x in headers:
    #        h[x] = headers[x]

    if 'Content-Type' in headers \
        and 'application/json' in headers['Content-Type'] \
        and request.method in ('POST', 'PUT'):
        payload = request.json
    else:
        payload = dict(request.args)
        payload.update(dict(request.form))

    return (payload, h)

def find_record(work):
    """
    Given a work in an ORCID XML profile, extract some metadata
    """

    # seconds since epoch
    updated = datetime.fromtimestamp(work['last-modified-date']['value'] / 1000.).isoformat()

    docs = work['work-summary']
    id0 = False

    try:
        tmp = work['external-ids']['external-id'][0]['external-id-type']
    except IndexError:
        # no ID is given, so get the putcode and the metadata from the first record
        id0 = str(work['work-summary'][0]['put-code'])
        status = 'not in ADS'
        title = work['work-summary'][0]['title']['title']['value']
        try:
            pubyear = work['work-summary'][0]['publication-date']['year']['value']
        except TypeError:
            pubyear = None
        try:
            pubmonth = work['work-summary'][0]['publication-date']['month']['value']
        except TypeError:
            pubmonth = None
        sources = []
        for doc in docs:
            sources.append(doc['source']['source-name']['value'])

        return id0, {id0: {'identifier': id0,
                           'status': status,
                           'title': title,
                           'pubyear': pubyear,
                           'pubmonth': pubmonth,
                           'updated': updated,
                           'putcode': id0,
                           'source': sources
                           }
                     }

    hasBibcode = False
    sources = []
    for doc in docs:
        ids = doc['external-ids']['external-id']
        # have to loop through all docs because BBB wants all sources
        sources.append(doc['source']['source-name']['value'])
        for d in ids:
            if d['external-id-type'] == 'bibcode':
                hasBibcode = True
                # stop if you find a bibcode
                id0 = d['external-id-value']
                status = 'pending'
                title = doc['title']['title']['value']
                putcode = doc['put-code']
                try:
                    pubyear = doc['publication-date']['year']['value']
                except TypeError:
                    pubyear = None
                try:
                    pubmonth = doc['publication-date']['month']['value']
                except TypeError:
                    pubmonth = None

                break

            elif d['external-id-type'] == 'doi':
                id0 = d['external-id-value']

        if (id0 and not hasBibcode):
            # save off the metadata for a DOI record in case we can't find a bibcode later
            status = 'pending'
            title = doc['title']['title']['value']
            putcode = doc['put-code']
            try:
                pubyear = doc['publication-date']['year']['value']
            except TypeError:
                pubyear = None
            try:
                pubmonth = doc['publication-date']['month']['value']
            except TypeError:
                pubmonth = None

    if id0:
        # return metadata for a bibcode or DOI record
        return id0, {id0: {'identifier': id0,
                           'status': status,
                           'title': title,
                           'pubyear': pubyear,
                           'pubmonth': pubmonth,
                           'updated': updated,
                           'putcode': putcode,
                           'source': sources
                           }
                     }
    else:
        # any given IDs are not bibcode or DOI, so get the putcode and the metadata from the first record
        id0 = str(work['work-summary'][0]['put-code'])
        status = 'not in ADS'
        title = work['work-summary'][0]['title']['title']['value']
        putcode = work['work-summary'][0]['put-code']
        try:
            pubyear = work['work-summary'][0]['publication-date']['year']['value']
        except TypeError:
            pubyear = None
        try:
            pubmonth = work['work-summary'][0]['publication-date']['month']['value']
        except TypeError:
            pubmonth = None

        return id0, {id0: {'identifier': id0,
                           'status': status,
                           'title': title,
                           'pubyear': pubyear,
                           'pubmonth': pubmonth,
                           'updated': updated,
                           'putcode': putcode,
                           'source': sources
                           }
                     }