import logging
from smtplib import SMTPRecipientsRefused
from zope import component
from Products.CMFCore.utils import getToolByName
from slc.eventinvite.adapter import IAttendeesStorage
from slc.eventinvite import MessageFactory as _

log = logging.getLogger(__name__)

def save_attendees(context, data):
    mtool = getToolByName(context, 'portal_membership')
    gtool = getToolByName(context, 'portal_groups')
    storage = IAttendeesStorage(context)
    group_ids = gtool.getGroupIds()
    internal_attendees = [] 
    groups = []
    for name in data['internal_attendees']:
        if name in group_ids:
            group = gtool.getGroupById(name)
            groups.append({
                'name': group.id,
                'confirmation': [], # Will contain list of userids of group 
                                    # members who have confirmed attendence
                })
        else:
            member = mtool.getMemberById(name)
            internal_attendees.append({
                'name': member.getProperty('fullname', None) or member.id,
                'email': member.getProperty('email'),
                'id': member.id,
                })
    storage.internal_attendees = internal_attendees
    storage.external_attendees = data['external_attendees']
    storage.groups = groups
    return {'internal_attendees': storage.internal_attendees,
            'external_attendees': storage.external_attendees,
            'groups': storage.groups,
            }

def send_email(context, recipient, mailview):
    host = getToolByName(context, 'MailHost')
    mtool = getToolByName(context, 'portal_membership')
    member = mtool.getAuthenticatedMember()
    try:
        host.send(
            mailview.render(recipient['name']), 
            mto=recipient['email'],
            mfrom=u'%s <%s>' % (mailview.email_from_name[0], 
                                mailview.email_from_address[0]),
            subject=context.Title().decode('utf-8'), 
            immediate=True,
            charset='utf-8',
            msg_type='text/html',
            )
    except SMTPRecipientsRefused:
        log.error(_(u"Error: %s's email address, %s, was rejected by the " \
                u"server." % (recipient['name'], recipient['email'])))


def email_recipients(view, context, data):
    mail_template = component.getMultiAdapter(
                                    (context, view.request),
                                    name="mail_attendees")

    for key in ['internal_attendees', 'external_attendees']:
        for recipient in data[key]:
            if not recipient['email']:
                continue
            send_email(context, recipient, mail_template)

    gtool = getToolByName(context, 'portal_groups')
    for group in data.get('groups', []):
        for gdict in data[key]:
            group = gtool.getGroupById(gdict['name'])
            for member in group.getGroupMembers():
                recipient = {}
                recipient['name'] = member.getProperty('fullname', member.id)
                recipient['email'] = member.getProperty('email')
                if not recipient['email']:
                    continue
                send_email(context, recipient, mail_template)


