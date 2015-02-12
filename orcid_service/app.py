from flask import Flask
from flask import current_app, request
from flask.ext.discoverer import Discoverer, advertise
import config
import requests

app = Flask(__name__, static_folder=None)
discoverer = Discoverer(app)

@advertise(scopes=['ads:default'], methods=['OPTIONS', 'GET'])
@app.route('/exchangeOAuthCode')
def getAccessToken():
    '''Exchange 'code' for 'access_token' data'''
    payload = dict(request.args)
    if 'code' not in payload:
        raise Exception('Parameter code is missing')
    headers = dict(Accept='application/json')
    data = {
      'client_id': config.ORCID_CLIENT_ID,
      'client_secret': config.ORCID_CLIENT_SECRET,
      'code': payload['code'][0],
      'grant_type': 'authorization_code'
    }
    r = requests.post(config.ORCID_OAUTH_ENDPOINT, data=data, headers=headers)
    return r.text, r.status_code

@advertise(scopes=['ads:default'], methods=['OPTIONS', 'GET', 'POST'])
@app.route('/<orcid_id>/orcid-profile')
def orcidProfile(orcid_id):
    '''Get/Set /[orcid-id]/orcid-profile'''
    payload, headers = check_request(request)
    if request.method == 'GET':
        print 'doing get', config.ORCID_API_ENDPOINT + '/' + orcid_id + '/orcid-profile', headers
        r = requests.get(config.ORCID_API_ENDPOINT + '/' + orcid_id + '/orcid-profile',
                         headers=headers)
    else:
        r = requests.post(config.ORCID_API_ENDPOINT + '/' + orcid_id + '/orcid-profile',
                         data=payload, headers=headers)
    return r.text, r.status_code

@advertise(scopes=['ads:default'], methods=['OPTIONS', 'GET', 'POST', 'PUT'])
@app.route('/<orcid_id>/orcid-works')
def orcidWorks(orcid_id):
    '''Get/Set /[orcid-id]/orcid-profile'''
    payload, headers = check_request(request)
    if request.method == 'GET':
        r = requests.get(config.ORCID_API_ENDPOINT + '/' + orcid_id + '/orcid-works', 
                      headers=headers)
    elif request.method == 'PUT':
        r = requests.put(config.ORCID_API_ENDPOINT + '/' + orcid_id + '/orcid-works', 
                      data=payload, headers=headers)
    else:
        r = requests.post(config.ORCID_API_ENDPOINT + '/' + orcid_id + '/orcid-works', 
                      data=payload, headers=headers)
    return r.text, r.status_code

    

def check_request(request):
    payload = dict(request.args)
    payload.update(dict(request.form))
    headers = dict(request.headers)
    if 'Orcid-Authorization' not in headers:
        raise Exception('Header Orcid-Authorization is missing')
    h = {'Accept': 'application/json', 'Authorization': headers['Orcid-Authorization']}
    for x in ['Content-Type']:
        if x in headers:
            h[x] = headers[x]
    return (payload, h)

if __name__ == '__main__':
    app.run(host='127.0.0.1',port=5000, debug=True)
