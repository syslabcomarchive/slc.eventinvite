from smtplib import SMTPRecipientsRefused
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from Products.CMFCore.utils import getToolByName
from slc.eventinvite.adapter import IAttendeesStorage
from slc.eventinvite import MessageFactory as _

def save_attendees(context, data):
    mtool = getToolByName(context, 'portal_membership')
    gtool = getToolByName(context, 'portal_groups')
    storage = IAttendeesStorage(context)
    internal_attendees = [] 
    groups = []
    for name in data['internal_attendees']:
        group = gtool.getGroupById(name)
        if group is None:
            member = mtool.getMemberById(name)
            internal_attendees.append({
                'name': member.getProperty('fullname', None) or member.id,
                'email': member.getProperty('email'),
                'id': member.id,
                })
        else:
            groups.append({
                'name': group.id,
                'confirmation': [], # Will contain list of userids of group 
                                    # members who have confirmed attendence
                })
    storage.internal_attendees = internal_attendees
    storage.external_attendees = data['external_attendees']
    storage.groups = groups
    return {'internal_attendees': storage.internal_attendees,
            'external_attendees': storage.external_attendees,
            'groups': storage.groups,
            }

def send_email(view, context, recipient, template):
    mtool = getToolByName(context, 'portal_membership')
    member = mtool.getAuthenticatedMember()
    host = getToolByName(context, 'MailHost')
    portal_url = getToolByName(context, 'portal_url')
    site = portal_url.getPortalObject()
    email_from_name = site.getProperty('email_from_name')
    email_from_address  = site.getProperty('email_from_address')
    mail_text = template(
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
            msg_type='text/html',
            )
    except SMTPRecipientsRefused:
        view.status = \
            _(u"Error: %s's email address, %s, was rejected by the " \
                u"server." % (recipient['name'], recipient['email']))


def email_recipients(view, context, data):
    for key in ['internal_attendees', 'external_attendees']:
        mail_template = ViewPageTemplateFile('browser/templates/mail_%s.pt' % key)
        for recipient in data[key]:
            if not recipient['email']:
                continue
            send_email(view, context, recipient, mail_template)

    for group in data.get('groups', []):
        # XXX: During confirmation, we need to somehow be aware from which group the user is...
        mail_template = ViewPageTemplateFile('browser/templates/mail_internal_attendees.pt' % key)
        for group in data[key]:
            for member in group.getGroupMembers():
                recipient = {}
                recipient['name'] = member.getProperty('fullname', member.id)
                recipient['email'] = member.getProperty('email')
                if not recipient['email']:
                    continue
                send_email(view, context, recipient, mail_template)

