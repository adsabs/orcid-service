import unittest
from orcid_service import app
from orcid_service.tests.base import TestCaseDatabase


class TestWebservices(TestCaseDatabase):
    '''Tests that each route is an http response'''

    def create_app(self):
        '''Start the wsgi application'''
        a = app.create_app(**{
            'SQLALCHEMY_DATABASE_URI': self.postgresql_url
           })
        return a

    def test_ResourcesRoute(self):
        '''Tests for the existence of a /resources route, and that it returns properly formatted JSON data'''
        r = self.client.get('/resources')
        self.assertEqual(r.status_code,200)
        [self.assertIsInstance(k, str) for k in r.json] #Assert each key is a string-type

        for expected_field, _type in {'scopes': list,
                                      'methods': list,
                                      'description': str,
                                      'rate_limit': list}.items():
            [self.assertIn(expected_field,v) for v in r.json.values()] #Assert each resource is described has the expected_field
            [self.assertIsInstance(v[expected_field],_type) for v in r.json.values()] #Assert every expected_field has the proper type


if __name__ == '__main__':
    unittest.main()
