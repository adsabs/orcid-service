from flask import current_app, request, Blueprint
from flask.ext.discoverer import advertise
from .models import db, User
import requests
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
    r = requests.post(current_app.config['ORCID_OAUTH_ENDPOINT'], data=data, headers=headers)
    
    # update/create user account
    data = r.json()
    if 'orcid' in data:
        u = db.session.query(User).filter_by(orcid_id=data['orcid']).first()
        if not u:
            u = User(orcid_id=data['orcid'], created=datetime.utcnow())
        u.updated = datetime.utcnow()
        u.access_token = data['access_token']
        # save the user
        db.session.begin_nested()
        try:
            db.session.add(u)
            db.session.commit()
        except exc.IntegrityError as e:
            db.session.rollback()
        # per PEP-0249 a transaction is always in progress    
        db.session.commit()
    
    return r.text, r.status_code


@advertise(scopes=[], rate_limit = [1000, 3600*24])
@bp.route('/<orcid_id>/orcid-profile', methods=['GET', 'POST'])
def orcid_profile(orcid_id):
    '''Get/Set /[orcid-id]/orcid-profile - all communication exclusively in JSON'''
    payload, headers = check_request(request)
    if request.method == 'GET':
        r = requests.get(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/record',
                         headers=headers)
    else:
        r = requests.post(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/record',
                         json=payload, headers=headers)
    
    # save the profile data (just in case the user revokes access_token, we can still get the update
    # from our local data); however - normally the updater should grab the latest data from orcid
    if r.status_code == 200:
        update_profile(orcid_id, r.text)
    
    return r.text, r.status_code


@advertise(scopes=[], rate_limit = [1000, 3600*24])
@bp.route('/<orcid_id>/orcid-works', methods=['GET', 'POST', 'PUT'])
def orcid_works(orcid_id):
    '''Get/Set /[orcid-id]/orcid-works - all communication exclusively in JSON'''

    payload, headers = check_request(request)

    if request.method == 'GET':
        r = requests.get(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/works',
                      headers=headers)
    elif request.method == 'PUT':
        r = requests.put(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/works',
                      json=payload, headers=headers)
        update_profile(orcid_id)
    elif request.method == 'POST':
        r = requests.post(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/works',
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
    recs = db.session.query(User).filter(User.updated >= latest_point) \
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
    
    u = db.session.query(User).filter_by(orcid_id=orcid_id).first()
    if not u:
        return json.dumps({'error': 'We do not have a record for: %s' % user_id}), 404
    
    if not u.access_token:
        return json.dumps({'error': 'We do not have access_token for: %s' % user_id}), 404
    
    out = u.toJSON()
    
    payload = dict(request.args)
    if payload.get('reload', False):
        h = {
             'Accept': 'application/json', 
             'Authorization': 'Bearer %s' % u.access_token,
             'Content-Type': 'application/json'
             }
        
        r = requests.get(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/record',
                         headers=h)
        if r.status_code == 200:
            # update our record (but avoid setting the updated date)
            j = r.json()
            db.session.begin_nested()
            try:
                u.profile = json.dumps(j)
                db.session.add(u)
                db.session.commit()
                out['profile'] = j
            except exc.IntegrityError as e:
                db.session.rollback()
            # per PEP-0249 a transaction is always in progress    
            db.session.commit()
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
        u = db.session.query(User).filter(and_(User.orcid_id==orcid_id, User.access_token==access_token)).first()
        if not u:
            return '{}', 404 # not found
        return u.info or '{}', 200
    elif request.method == 'POST':
        d = json.dumps(payload)
        if len(d) > current_app.config.get('MAX_ALLOWED_JSON_SIZE', 1000):
            return json.dumps({'msg': 'You have exceeded the allowed storage limit, no data was saved'}), 400
        u = db.session.query(User).filter(and_(User.orcid_id==orcid_id, User.access_token==access_token)).first()
        if not u:
            return json.dumps({'error': 'We do not have a record for: %s' % orcid_id}), 404
    
        u.info = d
    
        db.session.begin_nested()
        try:
            db.session.merge(u)
            db.session.commit()
        except exc.IntegrityError:
            db.session.rollback()
            return json.dumps({'msg': 'We have hit a db error! The world is crumbling all around... (eh, btw, your data was not saved)'}), 500
    
        # per PEP-0249 a transaction is always in progress    
        db.session.commit()
        return d, 200
    
    
def update_profile(orcid_id, data=None):
    """Inserts data into the user record and updates the 'updated'
    column with the most recent timestamp"""
    
    u = db.session.query(User).filter_by(orcid_id=orcid_id).first()
    if u:
        u.updated = datetime.utcnow()
        if data:
            try:
                #verify the data is a valid JSON
                d = json.loads(data)
                u.profile = json.dumps(d)
            except:
                logging.error('Invalid data passed in for {} (ignoring it)'.format(orcid_id))
                logging.error(data)
        # save the user
        db.session.begin_nested()
        try:
            db.session.add(u)
            db.session.commit()
        except exc.IntegrityError as e:
            db.session.rollback()
        # per PEP-0249 a transaction is always in progress    
        db.session.commit()
        
        
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
