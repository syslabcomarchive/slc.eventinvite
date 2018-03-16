import transaction
import unittest2 as unittest
from plone.testing.z2 import Browser
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import TEST_USER_PASSWORD
from plone.app.testing import setRoles
from plone.app.testing import login

from slc.eventinvite.testing import \
    SLC_EVENTINVITE_FUNCTIONAL_TESTING

from slc.eventinvite.testing import TestMixin

class TestFunctional(unittest.TestCase, TestMixin):
    layer = SLC_EVENTINVITE_FUNCTIONAL_TESTING

    @unittest.skip('FIXME')
    def test_functional(self):
        """ """
        portal = self.layer['portal']
        app = self.layer['app']
        browser = Browser(app)
        browser.handleErrors = False

        self.register_users()

        login(portal, TEST_USER_NAME)
        setRoles(portal, TEST_USER_ID, ('Manager',))
        id = portal.invokeFactory(
                            'Event', 
                            'plone-conference',
                            title='Plone Conference')
        transaction.commit()

        browser.open(portal.absolute_url() + '/login_form')
        browser.getControl(name='__ac_name').value = TEST_USER_NAME
        browser.getControl(name='__ac_password').value = TEST_USER_PASSWORD
        browser.getControl(name='submit').click()

        browser.open('%s/@@invite-attendees' % portal['plone-conference'].absolute_url())
        # XXX: Can't set the value of the UserAndGroupSelectionWidget because the <select> 
        # doesn't have any <option> elements to choose from. Instead it's populated via 
        # javascript which we cannot do via zc.testbrowser.
        att = browser.getControl(name="form.widgets.internal_attendees:list")
        name = browser.getControl(name='form.widgets.external_attendees.AA.widgets.name')
        email = browser.getControl(name='form.widgets.external_attendees.AA.widgets.email')
        email_all = browser.getControl(name="form.buttons.email_all")

