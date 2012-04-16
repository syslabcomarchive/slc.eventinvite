import unittest2 as unittest

from plone.testing import z2
from plone.app.testing import SITE_OWNER_NAME

from slc.eventinvite import utils
from slc.eventinvite.testing import TestMixin
from slc.eventinvite.adapter import IAttendeesStorage
from slc.eventinvite.testing import \
    SLC_EVENTINVITE_INTEGRATION_TESTING

class TestContent(unittest.TestCase, TestMixin):
    layer = SLC_EVENTINVITE_INTEGRATION_TESTING

    def test_save_attendees(self):
        """ """
        portal = self.layer['portal']
        app = self.layer['app']
        z2.login(app['acl_users'], SITE_OWNER_NAME)
        self.register_users()
        id = portal.invokeFactory(
                            'Event', 
                            'plone-conference',
                            title='Plone Conference')
        event = portal['plone-conference']

        storage = IAttendeesStorage(event)
        self.assertFalse(hasattr(storage, 'internal_attendees'))
        self.assertFalse(hasattr(storage, 'external_attendees'))
        self.assertFalse(hasattr(storage, 'groups'))

        data = {
            'internal_attendees': ['max-musterman', 'john-doe','Administrators'],
            'external_attendees': [{'name':'John Smith', 
                                    'email':'john@mail.com',}],
        }
        utils.save_attendees(event, data)

        self.assertTrue(hasattr(storage, 'internal_attendees'))
        self.assertTrue(hasattr(storage, 'external_attendees'))
        self.assertTrue(hasattr(storage, 'groups'))

        self.assertEqual(storage.internal_attendees, [
            {'id': 'max-musterman', 'name': 'max-musterman', 'email': ''}, 
            {'id': 'john-doe', 'name': 'john-doe', 'email': ''}])

        self.assertEqual(storage.external_attendees, [
            {'name': 'John Smith', 'email': 'john@mail.com'}])

        self.assertEqual(storage.groups, [
            {'name': 'Administrators', 'confirmation':[]}])

