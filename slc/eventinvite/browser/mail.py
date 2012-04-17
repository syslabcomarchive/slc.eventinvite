from five import grok
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from Products.CMFCore.utils import getToolByName
from Products.ATContentTypes.interfaces import IATEvent
from slc.eventinvite.interfaces import IProductLayer

grok.templatedir("templates")

class MailTemplate(grok.View):
    """ """
    grok.name('mail_attendees')
    grok.context(IATEvent)
    grok.layer(IProductLayer)
    grok.require('cmf.ModifyPortalContent')

    def __init__(self, context, request):
        """ """
        super(MailTemplate, self).__init__(context, request)
        mtool = getToolByName(context, 'portal_membership')
        self.sender = mtool.getAuthenticatedMember()

        portal_url = getToolByName(context, 'portal_url')
        site = portal_url.getPortalObject()
        email_from_name = site.getProperty('email_from_name')
        email_from_address  = site.getProperty('email_from_address')
        self.email_from_name = email_from_name,
        self.email_from_address = email_from_address,

    def render(self, recipient):
        self.recipient = recipient
        template = ViewPageTemplateFile('templates/mail_internal_attendees.pt')
        return template(self)


