from flask import current_app, request, Blueprint
from flask.ext.discoverer import advertise
from .models import db, User
import requests
from datetime import datetime
from dateutil import parser
from sqlalchemy import exc
import json

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
        r = requests.get(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/orcid-profile',
                         headers=headers)
    else:
        r = requests.post(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/orcid-profile',
                         json=payload, headers=headers)
    
    # save the profile data (just in case the user revokes access_token, we can still get the update
    # from our local data); however - normally the updater should grab the latest data from orcid
    update_profile(orcid_id, r.text)
    
    return r.text, r.status_code


@advertise(scopes=[], rate_limit = [1000, 3600*24])
@bp.route('/<orcid_id>/orcid-works', methods=['GET', 'POST', 'PUT'])
def orcid_works(orcid_id):
    '''Get/Set /[orcid-id]/orcid-works - all communication exclusively in JSON'''

    payload, headers = check_request(request)

    if request.method == 'GET':
        r = requests.get(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/orcid-works', 
                      headers=headers)
    elif request.method == 'PUT':
        r = requests.put(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/orcid-works', 
                      json=payload, headers=headers)
        update_profile(orcid_id)
    elif request.method == 'POST':
        r = requests.post(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/orcid-works', 
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
    
    # poorman's version of paging, but it works because the time resolution is in 
    # microseconds
    output = []
    recs = db.session.query(User).filter(User.updated >= latest_point) \
        .order_by(User.updated.desc()) \
        .limit(100).all()

    for r in recs:
        output.append({'orcid_id': r.orcid_id, 'created': r.created.isoformat(), 'updated': r.updated.isoformat(), 'profile': r.profile})
    
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
    
    h = {
         'Accept': 'application/json', 
         'Authorization': 'Bearer:%s' % u.access_token,
         'Content-Type': 'application/json'
         }
    
    r = requests.get(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/orcid-profile',
                         headers=h)
    
    return r.text, r.status_code


def update_profile(orcid_id, data=None):
    """Inserts data into the user record and updates the 'updated'
    column with the most recent timestamp"""
    
    u = db.session.query(User).filter_by(orcid_id=orcid_id).first()
    if u:
        u.updated = datetime.utcnow()
        if data:
            u.profile = data
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