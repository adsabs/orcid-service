from flask import url_for
import unittest
import json
import httpretty
from orcid_service.models import User, Profile
from orcid_service.views import update_profile_local
from orcid_service.tests.base import TestCaseDatabase
from .stubdata import orcid_profile, orcid_profile_api_v2, orcid_profile_api_v2_short, orcid_profile_api_v2_empty, \
    orcid_profile_api_v2_personaldetails, works_bulk, work_single, work_single_409, orcid_aa


class TestServices(TestCaseDatabase):


    @httpretty.activate
    def test_exchangeOAuthCode(self):
        client_id = self.app.config.get('ORCID_CLIENT_ID')
        client_secret = self.app.config.get('ORCID_CLIENT_SECRET')
        def request_callback(request, uri, headers):
            assert request.headers['Accept'] == 'application/json'
            assert request.parsed_body['code'] == ['exWxfg']
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
            httpretty.POST, self.app.config.get('ORCID_OAUTH_ENDPOINT'),
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
                assert request.body.decode('utf-8') == json.dumps({'foo': 'bar'})
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
    def test_orcid_profile_local(self):
        def request_callback(request, uri, headers):
            assert request.headers['Accept'] == 'application/json'
            assert request.headers['Content-Type'] == 'application/json'

            if request.method == 'GET':
                return (200, headers, json.dumps(orcid_profile_api_v2.data))

        def request_second_callback(request, uri, headers):
            assert request.headers['Accept'] == 'application/json'
            assert request.headers['Content-Type'] == 'application/json'

            if request.method == 'GET':
                return (200, headers, json.dumps(orcid_profile_api_v2_short.data))

        def request_empty_callback(request, uri, headers):
            assert request.headers['Accept'] == 'application/json'
            assert request.headers['Content-Type'] == 'application/json'

            if request.method == 'GET':
                return (200, headers, json.dumps(orcid_profile_api_v2_empty.data))

        httpretty.register_uri(
            httpretty.GET, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8868-9743/record',
            content_type='application/json',
            body=request_callback)

        r = self.client.get('/0000-0001-8868-9743/orcid-profile/simple?update=True',
                headers={'Orcid-Authorization': 'secret'})

        self.assertStatus(r, 200)
        self.assertEqual(len(r.json), 7)

        s = self.client.get('/0000-0001-8868-9743/orcid-profile/full',
                headers={'Orcid-Authorization': 'secret'})

        self.assertStatus(s, 200)
        self.assertEqual(len(s.json), 9)
        self.assertEqual(len(s.json['2015ApJ...810..149L']['source']),2)
        for _, value in s.json.items():
            putcode = value.get('putcode', None)
            self.assertTrue(type(putcode), str)

        httpretty.register_uri(
            httpretty.GET, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8868-9743/record',
            content_type='application/json',
            body=request_second_callback)

        f = self.client.get('/0000-0001-8868-9743/orcid-profile/full?update=True',
                            headers={'Orcid-Authorization': 'secret'})

        self.assertStatus(f, 200)
        self.assertEqual(len(f.json), 1)

        # make sure we're handling a profile with no works
        httpretty.register_uri(httpretty.GET, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0003-0931-6047/record',
            content_type='application/json',
            body=request_empty_callback)

        e = self.client.get('/0000-0003-0931-6047/orcid-profile/full?update=True',
                            headers={'Orcid-Authorization': 'secret'})

        self.assertStatus(e, 200)
        self.assertEqual(len(e.json), 0)

    @httpretty.activate
    def test_orcid_works(self):
        def request_callback(request, uri, headers):
            assert request.headers['Accept'] == 'application/json'
            assert request.headers['Content-Type'] == 'application/json'
            
            if (request.method == 'GET') & (',' in uri.split('/')[-1]):
                return (200, headers, json.dumps(works_bulk.data))
            elif request.method == 'GET':
                return (200, headers, json.dumps(work_single.data))
            elif (request.method == 'POST') & (uri.split('/')[-1] == 'work'):
                assert request.body.decode('utf-8') == json.dumps({'foo': 'bar'})
                return (201, headers, '')  # orcid literally returns empty string for single works post
            elif (request.method == 'POST') & (uri.split('/')[-1] == 'works'):
                assert request.body.decode('utf-8') == json.dumps({'foo': 'bar'})
                return (200, headers, json.dumps(works_bulk.data))
            elif request.method == 'PUT':
                assert request.body.decode('utf-8') == json.dumps({'foo': 'bar'})
                return (200, headers, json.dumps(work_single.data))
            elif request.method == 'DELETE':
                return (204, headers, '') # returns empty string
    
        httpretty.register_uri(
            httpretty.GET, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/work/876970',
            content_type='application/json',
            body=request_callback)
        httpretty.register_uri(
            httpretty.GET, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/works/513293,513305',
            content_type='application/json',
            body=request_callback)
        httpretty.register_uri(
            httpretty.POST, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/work',
            content_type='application/json',
            body=request_callback)
        httpretty.register_uri(
            httpretty.POST, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/works',
            content_type='application/json',
            body=request_callback)
        httpretty.register_uri(
            httpretty.PUT, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/work/876970',
            content_type='application/json',
            body=request_callback)
        httpretty.register_uri(
            httpretty.DELETE, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/work/876970',
            content_type='application/json',
            body=request_callback)

        r = self.client.get('/0000-0001-8178-9506/orcid-works/876970',
                headers={'Orcid-Authorization': 'secret'})
        self.assertStatus(r, 200)
        self.assertIn('short-description', r.json)

        r = self.client.get('/0000-0001-8178-9506/orcid-works/513293,513305',
                            headers={'Orcid-Authorization': 'secret'})
        self.assertStatus(r, 200)
        self.assertIn('bulk', r.json)

        r = self.client.post('/0000-0001-8178-9506/orcid-work',
                headers={'Orcid-Authorization': 'secret'},
                data=json.dumps({'foo': 'bar'}),
                content_type='application/json')
        self.assertStatus(r, 201)

        r = self.client.post('/0000-0001-8178-9506/orcid-works',
                             headers={'Orcid-Authorization': 'secret'},
                             data=json.dumps({'foo': 'bar'}),
                             content_type='application/json')
        self.assertStatus(r, 200)
        self.assertIn('bulk', r.json)
        
        r = self.client.put('/0000-0001-8178-9506/orcid-works/876970',
                headers={'Orcid-Authorization': 'secret'},
                data=json.dumps({'foo': 'bar'}),
                content_type='application/json')
        self.assertStatus(r, 200)
        self.assertIn('short-description', r.json)

        r = self.client.delete('/0000-0001-8178-9506/orcid-works/876970',
                headers={'Orcid-Authorization': 'secret'})
        self.assertStatus(r, 204)

    @httpretty.activate
    def test_orcid_works_409(self):
        def request_callback(request, uri, headers):
            assert request.headers['Accept'] == 'application/json'
            assert request.headers['Content-Type'] == 'application/json'
            if json.loads(request.body) == work_single_409.data:
                return (409, headers, 'error')
            elif json.loads(request.body) == work_single_409.data_noarxiv:
                return (200, headers, json.dumps(work_single_409.data_noarxiv))
            else:
                assert False, 'Something went wrong in the test'

        # def request_callback_2(request, uri, headers):
        #     assert request.headers['Accept'] == 'application/json'
        #     assert request.headers['Content-Type'] == 'application/json'
        #     import pdb
        #     pdb.set_trace()
        #     assert request.body == json.dumps(work_single_409.data_noarxiv)
        #     return 200, headers

        httpretty.register_uri(
            httpretty.PUT, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/work/63945135',
            content_type='application/json',
            body=request_callback)

        # httpretty.register_uri(
        #     httpretty.PUT, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/work/63945135',
        #     content_type='application/json',
        #     body=json.dumps(work_single_409.data_noarxiv),
        #     status=200)

        r = self.client.put('/0000-0001-8178-9506/orcid-works/63945135',
                            headers={'Orcid-Authorization': 'secret'},
                            data=json.dumps(work_single_409.data),
                            content_type='application/json')

        self.assertStatus(r, 200)
        self.assertEqual(r.json, work_single_409.data_noarxiv)

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
            httpretty.PUT, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/work/123456',
            content_type='application/json',
            body='')
        httpretty.register_uri(
            httpretty.POST, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/work',
            content_type='application/json',
            body='')
        httpretty.register_uri(
            httpretty.GET, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/work/123456',
            content_type='application/json',
            body='')

        with self.app.session_scope() as session:
            u = session.query(User).filter_by(orcid_id='0000-0001-8178-9506').first()
            if u:
                session.delete(u)
                session.commit()
        
            # at the beginning, there is no user record
            u = session.query(User).filter_by(orcid_id='0000-0001-8178-9506').first()
            self.assertTrue(u is None)
        
        # everybody has to pass always through the access-token endpoint
        r = self.client.get(url_for('orcid.get_access_token'), query_string={'code': 'exWxfg'})

        with self.app.session_scope() as session:
            # which creates the user record
            u = session.query(User).filter_by(orcid_id='0000-0001-8178-9506').first()
            self.assertTrue(u.updated >= u.created)
            self.assertTrue(u.profile is None)

            # whenever they request a profile (we'll save it into our cache)
            updated = u.updated

        r = self.client.get('/0000-0001-8178-9506/orcid-profile',
                headers={'Orcid-Authorization': 'secret'})

        with self.app.session_scope() as session:
            u = session.query(User).filter_by(orcid_id='0000-0001-8178-9506').first()
            self.assertTrue(u.updated > updated)
            self.assertTrue(str(u.profile) == json.dumps({'profile': 'get'}))

            updated = u.updated

        r = self.client.post('/0000-0001-8178-9506/orcid-profile',
                headers={'Orcid-Authorization': 'secret'},
                data=json.dumps({'foo': 'bar'}),
                content_type='application/json')

        with self.app.session_scope() as session:
            u = session.query(User).filter_by(orcid_id='0000-0001-8178-9506').first()
            self.assertTrue(u.updated > updated)
            self.assertTrue(str(u.profile) == json.dumps({'profile': 'post'}))

            # and when they access orcid-works (and modify something)
            updated = u.updated

        r = self.client.get('/0000-0001-8178-9506/orcid-works/123456',
                headers={'Orcid-Authorization': 'secret'})

        with self.app.session_scope() as session:
            u = session.query(User).filter_by(orcid_id='0000-0001-8178-9506').first()
            self.assertTrue(u.updated == updated)
            self.assertTrue(str(u.profile) == json.dumps({'profile': 'post'}))
        
            # we do not update profile (only timestamp)
            updated = u.updated

        r = self.client.put('/0000-0001-8178-9506/orcid-works/123456',
                headers={'Orcid-Authorization': 'secret'},
                data=json.dumps({'foo': 'bar'}),
                content_type='application/json')

        with self.app.session_scope() as session:
            u = session.query(User).filter_by(orcid_id='0000-0001-8178-9506').first()
            self.assertTrue(u.updated > updated)
            self.assertTrue(str(u.profile) == json.dumps({'profile': 'post'}))
        
            updated = u.updated

        r = self.client.post('/0000-0001-8178-9506/orcid-work',
                headers={'Orcid-Authorization': 'secret'},
                data=json.dumps({'foo': 'bar'}),
                content_type='application/json')

        with self.app.session_scope() as session:
            u = session.query(User).filter_by(orcid_id='0000-0001-8178-9506').first()
            self.assertTrue(u.updated > updated)
            self.assertTrue(str(u.profile) == json.dumps({'profile': 'post'}))

            updated = u.updated.isoformat()
            updated_plus = u.updated.replace(microsecond=u.updated.microsecond + 1).isoformat()

        # check we can get export the data
        r = self.client.get('/export/%s' % updated,
                headers={'Orcid-Authorization': 'secret'})
        self.assertTrue(len(r.json) == 1)
        self.assertTrue(r.json[0]['created'])
        self.assertTrue(r.json[0]['orcid_id'])
        self.assertTrue(r.json[0]['updated'])
        self.assertTrue(r.json[0]['profile'])
        
        r = self.client.get('/export/%s' % updated_plus,
                headers={'Orcid-Authorization': 'secret'})
        self.assertTrue(len(r.json) == 0)
        
        r = self.client.get('/export/%s' % updated,
                query_string={'fields': ['created', 'orcid_id']},
                headers={'Orcid-Authorization': 'secret'})
        self.assertTrue(len(r.json) == 1)
        self.assertTrue('created' in r.json[0])
        self.assertTrue('orcid_id' in r.json[0])
        self.assertFalse('updated' in r.json[0])
        self.assertFalse('profile' in r.json[0])
        
        
        # and it can retrieve the data (for us)
        r = self.client.get('/get-profile/%s' % '0000-0001-8178-9506')
        self.assertTrue(r.json['profile'] == {u'profile': u'post'})
        r = self.client.get('/get-profile/%s?reload=true' % '0000-0001-8178-9506')
        self.assertTrue(r.json['profile'] == {u'profile': u'get'})

        # check we can save/get utf-8 data
        u = session.query(User).filter_by(orcid_id='0000-0001-8178-9506').first()
        u.profile = u'{"foo": "\xe9"}'
        session.commit()

        r = self.client.get('/export/%s' % updated,
                headers={'Orcid-Authorization': 'secret'})
        self.assertTrue(len(r.json) == 1)
        self.assertTrue(r.json[0]['created'])
        self.assertTrue(r.json[0]['profile'] == {"foo": u"\xe9"})

        def request_callback(request, uri, headers):
            assert request.headers['Accept'] == 'application/json'
            assert request.headers['Content-Type'] == 'application/json'
            if request.method == 'GET':
                return (200, headers, json.dumps(orcid_profile_api_v2_short.data))

        httpretty.register_uri(
            httpretty.GET, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8178-9506/record',
            content_type='application/json',
            body=request_callback)

        # check that we can update the profile
        r = self.client.get('/update-orcid-profile/%s' % '0000-0001-8178-9506')
        self.assertTrue(len(r.json) == 1)
        self.assertTrue(list(r.json.keys())[0] == '2018NatSR...8.2398L')

    def test_update_local_storage(self):
        with self.app.session_scope() as session:
            u = session.query(User).filter_by(access_token='key3511').first()
            if u:
                session.delete(u)
                session.commit()
            u = User(orcid_id='0000-0002-4110-3511', access_token='key3511')
            session.add(u)
            session.commit()

            p = session.query(Profile).filter_by(orcid_id='0000-0002-4110-3511').first()
            if p:
                session.delete(p)
                session.commit()
            p = Profile(orcid_id='0000-0002-4110-3511', bibcode={"2007ASPC..376..467A":
                                                               {"identifier": "2007ASPC..376..467A",
                                                                "status": "verified",
                                                                "title": "Closing the Loop: Linking Datasets to Publications and Back",
                                                                "pubyear": "2007", "pubmonth": "10",
                                                                "updated": "2022-05-25T04:08:54.757000+00:00",
                                                                "putcode": "26708993",
                                                                "source": ["NASA Astrophysics Data System"]},
                                                           "1989LNP...329..191A":
                                                               {"identifier": "1989LNP...329..191A",
                                                                "status": "verified",
                                                                "title": "An approach to heuristic exploitation of astronomers' knowledge in automatic interpretation of optical pictures",
                                                                "pubyear": "1989", "pubmonth": None,
                                                                "updated": "2022-06-07T16:29:47.871000+00:00",
                                                                "putcode": "111778579",
                                                                "source": ["NASA Astrophysics Data System"]},
                                                             "10.3847/1538-4365/ac6268": {
                                                                 "identifier": "10.3847/1538-4365/ac6268",
                                                                 "status": "pending",
                                                                 "title": "Best Practices for Data Publication in the Astronomical Literature",
                                                                 "pubyear": "2022", "pubmonth": "05",
                                                                 "updated": "2023-10-27T01:45:31.180000+00:00",
                                                                 "putcode": "111778373",
                                                                 "source": ["NASA Astrophysics Data System", "Crossref"]}
                                                             }
                        )
            session.add(p)
            session.commit()

        # check that we can update the stored profile
        update_profile_local(orcid_id='0000-0002-4110-3511', data=json.dumps(orcid_aa.data), force=True)

        with self.app.session_scope() as session:
            p = session.query(Profile).filter_by(orcid_id='0000-0002-4110-3511').first()

            self.assertEqual(p.bibcode.keys(), {"2022ApJS..260....5C", "2007ASPC..376..467A", "1989LNP...329..191A"})

    def test_store_preferences(self):
        '''Tests the ability to store data'''
        with self.app.session_scope() as session:
            u = session.query(User).filter_by(access_token='keyx').first()
            if u:
                session.delete(u)
                session.commit()
            u = User(orcid_id='test', access_token='keyx')
            session.add(u)
            session.commit()
            
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
        self.assertTrue(r.json == {}, 'missing empty json response')
        
        # try to save something broken (it has to be json)
        r = self.client.post(url_for('orcid.preferences', orcid_id='test'),
                headers={'Authorization': 'secret', 'Orcid-Authorization': 'Bearer:keyx'},
                data=json.dumps({'foo': 'bar'})[0:-2],
                content_type='application/json')
        
        self.assertStatus(r, 400)
        self.assertTrue(r.json['msg'], 'missing explanation')
        
        # save something
        r = self.client.post(url_for('orcid.preferences', orcid_id='test'),
                headers={'Authorization': 'secret', 'Orcid-Authorization': 'Bearer:keyx'},
                data=json.dumps({'foo': 'bar'}),
                content_type='application/json')
        
        self.assertStatus(r, 200)
        self.assertTrue(r.json['foo'] == 'bar', 'missing echo')
        
        # get it back
        r = self.client.get(url_for('orcid.preferences', orcid_id='test'),
                headers={'Authorization': 'secret', 'Orcid-Authorization': 'Bearer:keyx'},
                content_type='application/json')
        
        self.assertStatus(r, 200)
        self.assertTrue(r.json == {'foo': 'bar'}, 'missing data')

    def test_update_status(self):
        with self.app.session_scope() as session:
            p = session.query(Profile).filter_by(orcid_id='test').first()
            if p:
                session.delete(p)
                session.commit()
            p = Profile(orcid_id='test', bibcode={u'2018NatSR...8.2398L':
                                                    {u'status': u'pending',
                                                     u'pubyear': u'2018',
                                                     u'updated': u'2018-04-12T11:41:52.899000',
                                                     u'pubmonth': u'12',
                                                     u'title': u'Test title'}})
            session.add(p)
            session.commit()

        r = self.client.get(url_for('orcid.update_status', orcid_id='test'),
                            headers={'Orcid-Authorization': 'secret'},
                            content_type='application/json')

        self.assertStatus(r, 200)
        self.assertTrue(r.json == {'2018NatSR...8.2398L': 'pending'})

        r = self.client.post(url_for('orcid.update_status', orcid_id='test'),
                            headers={'Orcid-Authorization': 'secret'},
                            data=json.dumps({'bibcodes': '2018NatSR...8.2398L', 'status': 'verified'}),
                            content_type='application/json')

        self.assertStatus(r, 200)
        self.assertTrue(r.json == {u'2018NatSR...8.2398L': 'verified'})

    @httpretty.activate
    def test_get_orcid_name(self):

        def request_callback(request, uri, headers):
            assert request.headers['Accept'] == 'application/json'
            assert request.headers['Content-Type'] == 'application/json'

            if request.method == 'GET':
                return (200, headers, json.dumps(orcid_profile_api_v2_personaldetails.data))

        httpretty.register_uri(
            httpretty.GET, self.app.config['ORCID_API_ENDPOINT'] + '/0000-0001-8868-9743/personal-details',
            content_type='application/json',
            body=request_callback)

        r = self.client.get(url_for('orcid.orcid_name', orcid_id='0000-0001-8868-9743'),
                            headers={'Orcid-Authorization': 'secret'})

        self.assertStatus(r, 200)
        self.assertTrue(r.json['name']['family-name']['value'] == 'Payne')

if __name__ == '__main__':
  unittest.main()
