# -*- coding: utf-8 -*-
"""
    myads_service.models
    ~~~~~~~~~~~~~~~~~~~~~

    Models for the users (users) of AdsWS
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import Column, String, TIMESTAMP, Text
from adsmutils import UTCDateTime
import json
import logging

Base = declarative_base()

class MutableDict(Mutable, dict):
    """
    By default, SQLAlchemy only tracks changes of the value itself, which works
    "as expected" for simple values, such as ints and strings, but not dicts.
    http://stackoverflow.com/questions/25300447/
    using-list-on-postgresql-json-type-with-sqlalchemy
    """

    @classmethod
    def coerce(cls, key, value):
        """
        Convert plain dictionaries to MutableDict.
        """
        if not isinstance(value, MutableDict):
            if isinstance(value, dict):
                return MutableDict(value)

            # this call will raise ValueError
            return Mutable.coerce(key, value)
        else:
            return value

    def __setitem__(self, key, value):
        """
        Detect dictionary set events and emit change events.
        """
        dict.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        """
        Detect dictionary del events and emit change events.
        """
        dict.__delitem__(self, key)
        self.changed()

    def setdefault(self, key, value):
        """
        Detect dictionary setdefault events and emit change events
        """
        dict.setdefault(self, key, value)
        self.changed()

    def pop(self, key, default):
        """
        Detect dictionary pop events and emit change events
        :param key: key to pop
        :param default: default if key does not exist
        :return: the item under the given key
        """
        dict.pop(self, key, default)
        self.changed()

class User(Base):
    __tablename__ = 'users'
    
    orcid_id = Column(String(255), primary_key=True)
    access_token = Column(String(255))
    created = Column(TIMESTAMP)
    updated = Column(TIMESTAMP)
    profile = Column(Text)
    info = Column(Text)
    
    def toJSON(self):
        """Returns value formatted as python dict."""
        return {
            'orcid_id': self.orcid_id,
            'access_token': self.access_token,
            'created': self.created and self.created.isoformat() or None,
            'updated': self.updated and self.updated.isoformat() or None,
            'profile': self.profile and json.loads(self.profile) or None,
            'info': self.info and json.loads(self.info) or None
        }

class Profile(Base):
    __tablename__ = 'profile'

    orcid_id = Column(String(255), primary_key=True)
    created = Column(UTCDateTime)
    updated = Column(UTCDateTime)
    bibcode = Column(MutableDict.as_mutable(JSON), default={})

    bib_status = ['verified', 'pending', 'rejected']
    nonbib_status = ['not in ADS']

    keys = ['status', 'title', 'pubyear', 'pubmonth']

    def get_bibcodes(self):
        """
        Returns the bibcodes of the ORCID profile
        """
        bibcodes, statuses = self.find_nested(self.bibcode, 'status', self.bib_status)
        return bibcodes, statuses

    def get_non_bibcodes(self):
        """
        Returns the non-ADS records of the ORCID profile
        """
        non_bibcodes, status = self.find_nested(self.bibcode, 'status', self.nonbib_status)
        return non_bibcodes

    def get_records(self):
        """
        Returns all records from an ORCID profile
        """
        return self.bibcode

    def add_records(self, records):
        """
        Adds a record to the bibcode field, first making sure it has the appropriate nested dict
        :param records: dict of dicts of bibcodes and non-bibcodes
        """
        if not self.bibcode:
            self.bibcode = {}
        for r in records:
            for k in self.keys:
                tmp = records[r].setdefault(k, None)
        self.bibcode.update(records)

    def remove_bibcodes(self, bibcodes):
        """
        Removes a bibcode(s) from the bibcode field.
        Given the way in which bibcodes are stored may change, it seems simpler
        to keep the method of adding/removing in a small wrapper so that only
        one location needs to be modified (or YAGNI?).
        :param bibcodes: list of bibcodes
        """
        [self.bibcode.pop(key, None) for key in bibcodes]

    def get_nested(self, dictionary, nested_key):
        """Get all values from the nested dictionary for a given nested key"""
        keys = dictionary.keys()
        vals = []
        for key in keys:
            vals.append(dictionary[key].setdefault(nested_key, None))

        return vals

    def find_nested(self, dictionary, nested_key, nested_value):
        """Get all top-level keys from a nested dictionary for a given list of nested values
         belonging to a given nested key
         :param dictionary - nested dictionary to search; searches one level deep
         :param nested_key - key within nested dictionary to search for
         :param nested_value - list (or string or number) of acceptable values to search for within the
            given nested_key
         :return good_keys - list of top-level keys with a matching nested value to the given nested key
         :return good_values - list of the value (from nested_value) retrieved
         """
        if type(nested_value) is not list:
            nested_value = [nested_value]

        keys = dictionary.keys()
        good_keys = []
        good_values = []
        for key in keys:
            if dictionary[key].get(nested_key,'') in nested_value:
                good_keys.append(key)
                good_values.append(dictionary[key].get(nested_key))

        return good_keys, good_values

    def update_status(self, keys, status):
        """
        Update the status for a given key or keys
        :param keys: str or list
        :param status: str
        :return: None
        """
        if type(keys) is not list:
            keys = [keys]

        for key in keys:
            if key in self.bibcode:
                self.bibcode[key]['status'] = status
            else:
                logging.warning('Record %s not in profile for %s'.format(key, self.orcid_id))

    def get_status(self, keys):
        """
        For a given set of records, return the statuses
        :param keys: str or list
        :return: good_keys - list of keys that exist in the set
        :return: statuses - list of statuses of good_keys
        """
        if type(keys) is not list:
            keys = [keys]

        good_keys = []
        statuses = []

        for key in keys:
            if key in self.bibcode:
                good_keys.append(key)
                statuses.append(self.bibcode[key]['status'])

        return good_keys, statuses