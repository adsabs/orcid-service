import sys, os
from urllib import urlencode
PROJECT_HOME = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
sys.path.append(PROJECT_HOME)
from flask.ext.testing import TestCase
from flask import url_for, request
import unittest
import json
import httpretty
import app
import cgi
from StringIO import StringIO
from stubdata import orcid_profile

class TestServices(TestCase):
    '''Tests that each route is an http response'''

    def create_app(self):
        '''Start the wsgi application'''
        from views import app
        return app


    @httpretty.activate
    def test_exchangeOAuthCode(self):
        def request_callback(request, uri, headers):
            assert request.headers['Accept'] == 'application/json'
            assert request.parsed_body['code'] == [u'exWxfg']
            assert request.parsed_body['client_id'] == [u'APP-P5ANJTQRRTMA6GXZ']
            assert request.parsed_body['client_secret'] == [u'989e54c8-7093-4128-935f-30c19ed9158c']
            return (200, headers, """{
                "access_token":"44180096-5d32-49f7-bca1-1f67fd7f1b7d",
                "token_type":"bearer",
                "expires_in":3599,
                "scope":"/orcid-profile/read-limited /orcid-works/create /orcid-works/update",
                "orcid":"0000-0001-8178-9506",
                "name":"Roman Chyla"}""")
    
        httpretty.register_uri(
            httpretty.POST, self.app.config['ORCID_OAUTH_ENDPOINT'],
            content_type='application/json',
            body=request_callback)

        r = self.client.get(url_for('get_access_token'), query_string={'code': 'exWxfg'})
        self.assertStatus(r, 200)
        self.assertIn('access_token', r.json)


    @httpretty.activate
    def test_orcid_profile(self):
        def request_callback(request, uri, headers):
            assert request.headers['Accept'] == 'application/json'
            assert request.headers['Content-Type'] == 'application/json'
            
            if request.method == 'GET':
                return (200, headers, json.dumps(orcid_profile.data))
            elif request.method == 'POST':
                assert request.body == json.dumps({'foo': 'bar'})
                return (201, headers, '') # orcid literally returns empty string
    
        httpretty.register_uri(
            httpretty.GET, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/orcid-profile',
            content_type='application/json',
            body=request_callback)
        httpretty.register_uri(
            httpretty.POST, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/orcid-profile',
            content_type='application/json',
            body=request_callback)

        r = self.client.get('/0000-0001-8178-9506/orcid-profile',
                headers={'Orcid-Authorization': 'secret'})
        
        self.assertStatus(r, 200)
        self.assertIn('orcid-profile', r.json)
        
        
        r = self.client.post('/0000-0001-8178-9506/orcid-profile',
                headers={'Orcid-Authorization': 'secret'},
                data=json.dumps({'foo': 'bar'}),
                content_type='application/json')
        self.assertStatus(r, 201)
        
    
    @httpretty.activate
    def test_orcid_works(self):
        def request_callback(request, uri, headers):
            assert request.headers['Accept'] == 'application/json'
            assert request.headers['Content-Type'] == 'application/json'
            
            if request.method == 'GET':
                return (200, headers, json.dumps(orcid_profile.data))
            elif request.method == 'POST':
                assert request.body == json.dumps({'foo': 'bar'})
                return (201, headers, '') # orcid literally returns empty string
            elif request.method == 'PUT':
                assert request.body == json.dumps({'foo': 'bar'})
                return (201, headers, json.dumps(orcid_profile.data))
    
        httpretty.register_uri(
            httpretty.GET, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/orcid-works',
            content_type='application/json',
            body=request_callback)
        httpretty.register_uri(
            httpretty.POST, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/orcid-works',
            content_type='application/json',
            body=request_callback)
        httpretty.register_uri(
            httpretty.PUT, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/orcid-works',
            content_type='application/json',
            body=request_callback)

        r = self.client.get('/0000-0001-8178-9506/orcid-works',
                headers={'Orcid-Authorization': 'secret'})
        
        self.assertStatus(r, 200)
        self.assertIn('orcid-profile', r.json)
        
        
        r = self.client.post('/0000-0001-8178-9506/orcid-works',
                headers={'Orcid-Authorization': 'secret'},
                data=json.dumps({'foo': 'bar'}),
                content_type='application/json')
        self.assertStatus(r, 201)
        
        r = self.client.put('/0000-0001-8178-9506/orcid-works',
                headers={'Orcid-Authorization': 'secret'},
                data=json.dumps({'foo': 'bar'}),
                content_type='application/json')
        self.assertStatus(r, 201)
        self.assertIn('orcid-profile', r.json)
        
        
if __name__ == '__main__':
  unittest.main()
