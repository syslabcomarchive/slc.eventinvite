from smtplib import SMTPRecipientsRefused
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from Products.CMFCore.utils import getToolByName
from slc.eventinvite.adapter import IAttendeesStorage
from slc.eventinvite import MessageFactory as _

def save_attendees(context, data):
    mtool = getToolByName(context, 'portal_membership')
    storage = IAttendeesStorage(context)
    storage.internal_attendees = [] 
    for username in data['internal_attendees']:
        member = mtool.getMemberById(username)
        storage.internal_attendees.append({
            'name': member.getProperty('fullname', None) or member.id,
            'email': member.getProperty('email'),
            'id': member.id,
            })
    storage.external_attendees = data['external_attendees']
    return {'internal_attendees': storage.internal_attendees,
            'external_attendees': storage.external_attendees}

def email_recipients(view, context, data):
    mtool = getToolByName(context, 'portal_membership')
    member = mtool.getAuthenticatedMember()
    host = getToolByName(context, 'MailHost')
    portal_url = getToolByName(context, 'portal_url')
    site = portal_url.getPortalObject()
    email_from_name = site.getProperty('email_from_name')
    email_from_address  = site.getProperty('email_from_address')
    for key in ['internal_attendees', 'external_attendees']:
        mail_template = ViewPageTemplateFile('browser/templates/mail_%s.pt' % key)
        for recipient in data[key]:
            if not recipient['email']:
                continue
            mail_text = mail_template(
                            view,
                            recipient=recipient['name'],
                            sender=member,
                            email_from_name=email_from_name,
                            email_from_address=email_from_address,
                            event=context)
            try:
                host.send(
                    mail_text, 
                    mto=recipient['email'],
                    mfrom=u'%s <%s>' % (email_from_name, email_from_address),
                    subject=_("You have been invited to an event."), 
                    immediate=True,
                    charset='utf-8',
                    )
            except SMTPRecipientsRefused:
                view.status = \
                    _(u"Error: %s's email address, %s, was rejected by the " \
                        u"server." % (recipient['name'], recipient['email']))

