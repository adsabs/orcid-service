from flask.ext.testing import TestCase
from flask import url_for
import unittest
import json
import httpretty
from orcid_service import app
from orcid_service.models import db, User
from stubdata import orcid_profile

class TestServices(TestCase):

    def create_app(self):
        '''Start the wsgi application'''
        a = app.create_app({
            'SQLALCHEMY_BINDS' : {
                'orcid':        'sqlite:///'
            }
           })
        db.create_all(app=a)
        return a

    @httpretty.activate
    def test_exchangeOAuthCode(self):
        client_id = self.app.config['ORCID_CLIENT_ID']
        client_secret = self.app.config['ORCID_CLIENT_SECRET']
        def request_callback(request, uri, headers):
            assert request.headers['Accept'] == 'application/json'
            assert request.parsed_body['code'] == [u'exWxfg']
            assert request.parsed_body['client_id'] == [client_id]
            assert request.parsed_body['client_secret'] == [client_secret]
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

        r = self.client.get(url_for('orcid.get_access_token'), query_string={'code': 'exWxfg'})
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
            httpretty.GET, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/record',
            content_type='application/json',
            body=request_callback)
        httpretty.register_uri(
            httpretty.POST, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/record',
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
            httpretty.GET, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/works',
            content_type='application/json',
            body=request_callback)
        httpretty.register_uri(
            httpretty.POST, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/works',
            content_type='application/json',
            body=request_callback)
        httpretty.register_uri(
            httpretty.PUT, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/works',
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
        
    @httpretty.activate
    def test_persistence(self):
        httpretty.register_uri(
            httpretty.POST, self.app.config['ORCID_OAUTH_ENDPOINT'],
            content_type='application/json',
            body="""{
                "access_token":"44180096-5d32-49f7-bca1-1f67fd7f1b7d",
                "token_type":"bearer",
                "expires_in":3599,
                "scope":"/orcid-profile/read-limited /orcid-works/create /orcid-works/update",
                "orcid":"0000-0001-8178-9506",
                "name":"Roman Chyla"}""")
        httpretty.register_uri(
            httpretty.GET, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/record',
            content_type='application/json',
            body=json.dumps({'profile': 'get'}))
        httpretty.register_uri(
            httpretty.POST, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/record',
            content_type='application/json',
            body=json.dumps({'profile': 'post'}))
        httpretty.register_uri(
            httpretty.PUT, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/works',
            content_type='application/json',
            body='')
        httpretty.register_uri(
            httpretty.POST, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/works',
            content_type='application/json',
            body='')
        httpretty.register_uri(
            httpretty.GET, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/works',
            content_type='application/json',
            body='')
        
        u = db.session.query(User).filter_by(orcid_id='0000-0001-8178-9506').first()
        if u:
            db.session.delete(u)
            db.session.commit()
        
        # at the beginning, there is no user record
        u = db.session.query(User).filter_by(orcid_id='0000-0001-8178-9506').first()
        self.assertTrue(u is None)
        
        # everybody has to pass always through the access-token endpoint
        r = self.client.get(url_for('orcid.get_access_token'), query_string={'code': 'exWxfg'})
        
        # which creates the user record
        u = db.session.query(User).filter_by(orcid_id='0000-0001-8178-9506').first()
        self.assertTrue(u.updated >= u.created)
        self.assertTrue(u.profile is None)
        
        # whenever they request a profile (we'll save it into our cache)
        updated = u.updated
        r = self.client.get('/0000-0001-8178-9506/orcid-profile',
                headers={'Orcid-Authorization': 'secret'})
        self.assertTrue(u.updated > updated)
        self.assertTrue(str(u.profile) == json.dumps({'profile': 'get'}))

        updated = u.updated        
        r = self.client.post('/0000-0001-8178-9506/orcid-profile',
                headers={'Orcid-Authorization': 'secret'},
                data=json.dumps({'foo': 'bar'}),
                content_type='application/json')
        self.assertTrue(u.updated > updated)
        self.assertTrue(str(u.profile) == json.dumps({'profile': 'post'}))
        
        # and when they access orcid-works (and modify something)
        updated = u.updated
        r = self.client.get('/0000-0001-8178-9506/orcid-works',
                headers={'Orcid-Authorization': 'secret'})
        self.assertTrue(u.updated == updated)
        self.assertTrue(str(u.profile) == json.dumps({'profile': 'post'}))
        
        # we do not update profile (only timestamp)
        updated = u.updated
        r = self.client.put('/0000-0001-8178-9506/orcid-works',
                headers={'Orcid-Authorization': 'secret'},
                data=json.dumps({'foo': 'bar'}),
                content_type='application/json')
        self.assertTrue(u.updated > updated)
        self.assertTrue(str(u.profile) == json.dumps({'profile': 'post'}))
        
        updated = u.updated
        r = self.client.post('/0000-0001-8178-9506/orcid-works',
                headers={'Orcid-Authorization': 'secret'},
                data=json.dumps({'foo': 'bar'}),
                content_type='application/json')
        self.assertTrue(u.updated > updated)
        self.assertTrue(str(u.profile) == json.dumps({'profile': 'post'}))
        
        
        # check we can get export the data
        r = self.client.get('/export/%s' % u.updated.isoformat(),
                headers={'Orcid-Authorization': 'secret'})
        self.assertTrue(len(r.json) == 1)
        self.assertTrue(r.json[0]['created'])
        self.assertTrue(r.json[0]['orcid_id'])
        self.assertTrue(r.json[0]['updated'])
        self.assertTrue(r.json[0]['profile'])
        
        r = self.client.get('/export/%s' % u.updated.replace(microsecond=u.updated.microsecond + 1).isoformat(),
                headers={'Orcid-Authorization': 'secret'})
        self.assertTrue(len(r.json) == 0)
        
        r = self.client.get('/export/%s' % u.updated.isoformat(),
                query_string={'fields': ['created', 'orcid_id']},
                headers={'Orcid-Authorization': 'secret'})
        self.assertTrue(len(r.json) == 1)
        self.assertTrue(r.json[0].has_key('created'))
        self.assertTrue(r.json[0].has_key('orcid_id'))
        self.assertFalse(r.json[0].has_key('updated'))
        self.assertFalse(r.json[0].has_key('profile'))
        
        
        # and it can retrieve the data (for us)
        r = self.client.get('/get-profile/%s' % '0000-0001-8178-9506')
        self.assertTrue(r.json['profile'] == {u'profile': u'post'})
        r = self.client.get('/get-profile/%s?reload=true' % '0000-0001-8178-9506')
        self.assertTrue(r.json['profile'] == {u'profile': u'get'})
        
        # check we can save/get utf-8 data
        u = db.session.query(User).filter_by(orcid_id='0000-0001-8178-9506').first()
        u.profile = u'{"foo": "\xe9"}'
        db.session.commit()
        
        r = self.client.get('/export/%s' % u.updated.isoformat(),
                headers={'Orcid-Authorization': 'secret'})
        self.assertTrue(len(r.json) == 1)
        self.assertTrue(r.json[0]['created'])
        self.assertTrue(r.json[0]['profile'] == {"foo": u"\xe9"})


    def test_store_preferences(self):
        '''Tests the ability to store data'''
        u = db.session.query(User).filter_by(access_token='keyx').first()
        if u:
            db.session.delete(u)
            db.session.commit()
        u = User(orcid_id='test', access_token='keyx')
        db.session.add(u)
        db.session.commit()
            
        # wrong request (missing Orcid-Authorization)
        r = self.client.get(url_for('orcid.preferences', orcid_id='test'),
                headers={'Authorization': 'Bearer:secret'},
                data=json.dumps({'foo': 'bar'}),
                content_type='application/json')
        
        self.assertStatus(r, 400)
        
        # no data is there yet (get params ignored)
        r = self.client.get(url_for('orcid.preferences', orcid_id='test'),
                headers={'Authorization': 'secret', 'Orcid-Authorization': 'Bearer:keyx'},
                data=json.dumps({'foo': 'bar'}),
                content_type='application/json')
        
        self.assertStatus(r, 200)
        self.assert_(r.json == {}, 'missing empty json response')
        
        # try to save something broken (it has to be json)
        r = self.client.post(url_for('orcid.preferences', orcid_id='test'),
                headers={'Authorization': 'secret', 'Orcid-Authorization': 'Bearer:keyx'},
                data=json.dumps({'foo': 'bar'})[0:-2],
                content_type='application/json')
        
        self.assertStatus(r, 400)
        self.assert_(r.json['msg'], 'missing explanation')
        
        # save something
        r = self.client.post(url_for('orcid.preferences', orcid_id='test'),
                headers={'Authorization': 'secret', 'Orcid-Authorization': 'Bearer:keyx'},
                data=json.dumps({'foo': 'bar'}),
                content_type='application/json')
        
        self.assertStatus(r, 200)
        self.assert_(r.json['foo'] == 'bar', 'missing echo')
        
        # get it back
        r = self.client.get(url_for('orcid.preferences', orcid_id='test'),
                headers={'Authorization': 'secret', 'Orcid-Authorization': 'Bearer:keyx'},
                content_type='application/json')
        
        self.assertStatus(r, 200)
        self.assert_(r.json == {'foo': 'bar'}, 'missing data')
        
if __name__ == '__main__':
  unittest.main()
