from flask.ext.testing import TestCase
import unittest
from orcid_service import app


class TestWebservices(TestCase):
    '''Tests that each route is an http response'''
    def create_app(self):
        '''Start the wsgi application'''
        a = app.create_app(**{
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///'
           })
        return a

    def test_ResourcesRoute(self):
        '''Tests for the existence of a /resources route, and that it returns properly formatted JSON data'''
        r = self.client.get('/resources')
        self.assertEqual(r.status_code,200)
        [self.assertIsInstance(k, basestring) for k in r.json] #Assert each key is a string-type

        for expected_field, _type in {'scopes':list,'methods':list,'description':basestring,'rate_limit':list}.iteritems():
            [self.assertIn(expected_field,v) for v in r.json.values()] #Assert each resource is described has the expected_field
            [self.assertIsInstance(v[expected_field],_type) for v in r.json.values()] #Assert every expected_field has the proper type


if __name__ == '__main__':
    unittest.main()
