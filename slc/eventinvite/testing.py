from plone.testing.z2 import installProduct
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import applyProfile
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import IntegrationTesting
from plone.app.testing import FunctionalTesting

from zope.configuration import xmlconfig

class EventInviteFixture(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)
    
    def setUpZope(self, app, configurationContext):
        # Load ZCML
        import five.grok
        import slc.eventinvite
        import Products.UserAndGroupSelectionWidget
        xmlconfig.file('configure.zcml', five.grok, context=configurationContext)
        xmlconfig.file('configure.zcml', slc.eventinvite, context=configurationContext)
        xmlconfig.file('configure.zcml', Products.UserAndGroupSelectionWidget, context=configurationContext)
        installProduct(app, 'Products.UserAndGroupSelectionWidget')

    def setUpPloneSite(self, portal):
        applyProfile(portal, 'slc.eventinvite:default')

class TestMixin(object):
    
    def register_users(self):
        portal = self.layer['portal']
        test_users = [
            # username, password, group
            ('max-musterman', 'Max Musterman', 'max@mail.com', ''),
            ('john-doe', 'John Doe', 'john@mail.com', ''),
            ('jan-rap', 'Jan Rap', 'janrap@mail.com', 'Administrators'),
            ('andreas-ebersbacher', 'Andreas Ebersbacher', 'andreas@mail.com', ''),
            ('jan-keller', 'Jan Keller', 'jan@mail.com', 'Reviewers'),
            ('werner-wechsler', 'Werner Wechsler', 'werner@mail.com', 'Reviewers'),
            ]

        for username, fullname, email, group in test_users:
            if username not in portal.acl_users.getUserIds():
                membership = portal.portal_membership
                membership.addMember(username, 'secret', [], [])
                member = membership.getMemberById(username)
                member.setMemberProperties(
                            {'fullname': fullname, 'email': email})
                if group:
                    portal.portal_groups.addPrincipalToGroup(username, group)


SLC_EVENTINVITE_FIXTURE = EventInviteFixture()
SLC_EVENTINVITE_INTEGRATION_TESTING = \
        IntegrationTesting(
                bases=(SLC_EVENTINVITE_FIXTURE,), 
                name="EventInvite:Integration"
                )

SLC_EVENTINVITE_FUNCTIONAL_TESTING = \
        FunctionalTesting(
                bases=(SLC_EVENTINVITE_FIXTURE,), 
                name="EventInvite:Functional"
                )

