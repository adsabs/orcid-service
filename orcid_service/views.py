from flask import Flask
from flask import current_app, request
from flask.ext.discoverer import Discoverer, advertise
import requests

app = Flask(__name__, static_folder=None)
app.url_map.strict_slashes = False
app.config.from_pyfile('config.py')
try:
  app.config.from_pyfile('local_config.py')
except IOError:
  pass

discoverer = Discoverer(app)

@advertise(scopes=[], rate_limit = [100, 3600*24])
@app.route('/exchangeOAuthCode', methods=['GET'])
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
    return r.text, r.status_code

@advertise(scopes=[], rate_limit = [1000, 3600*24])
@app.route('/<orcid_id>/orcid-profile', methods=['GET', 'POST'])
def orcid_profile(orcid_id):
    '''Get/Set /[orcid-id]/orcid-profile - all communication exclusively in JSON'''
    payload, headers = check_request(request)
    if request.method == 'GET':
        r = requests.get(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/orcid-profile',
                         headers=headers)
    else:
        r = requests.post(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/orcid-profile',
                         json=payload, headers=headers)
    return r.text, r.status_code

@advertise(scopes=[], rate_limit = [1000, 3600*24])
@app.route('/<orcid_id>/orcid-works', methods=['GET', 'POST', 'PUT'])
def orcid_works(orcid_id):
    '''Get/Set /[orcid-id]/orcid-works - all communication exclusively in JSON'''
    
    payload, headers = check_request(request)
    
    if request.method == 'GET':
        r = requests.get(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/orcid-works', 
                      headers=headers)
    elif request.method == 'PUT':
        r = requests.put(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/orcid-works', 
                      json=payload, headers=headers)
    elif request.method == 'POST':
        r = requests.post(current_app.config['ORCID_API_ENDPOINT'] + '/' + orcid_id + '/orcid-works', 
                      json=payload, headers=headers)
    return r.text, r.status_code

    

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
        and headers['Content-Type'] == 'application/json' \
        and request.method in ('POST', 'PUT'):
        payload = request.json
    else:
        payload = dict(request.args)
        payload.update(dict(request.form))
    
    return (payload, h)

