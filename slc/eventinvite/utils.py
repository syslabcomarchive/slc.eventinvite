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


def email_recipients(context, data):
    mail_template = component.getMultiAdapter(
                                    (context, context.REQUEST),
                                    name="mail_attendees")

    for key in ['internal_attendees', 'external_attendees']:
        for recipient in data[key]:
            if not recipient['email']:
                continue
            send_email(context, recipient, mail_template)

    gtool = getToolByName(context, 'portal_groups')
    for gdict in data.get('groups', []):
        group = gtool.getGroupById(gdict['name'])
        if group is None:
            log.error("Could not get group '%s'" % gdict['name'])
            continue
        for member in group.getGroupMembers():
            recipient = {}
            recipient['name'] = member.getProperty('fullname', member.id)
            recipient['email'] = member.getProperty('email')
            if not recipient['email']:
                continue
            send_email(context, recipient, mail_template)


def get_new_attendees(context, data):
    """ Gets newly added attendees and returns a dictionary in the proper 
        format.

        $data is a dict, whose required format is the same as would be 
        submitted to the request by the z3c.form widgets as defined
        in browser/invite.py

        Here's an example:
        {
            'external_attendees': [
                    {'email': 'max@mail.com', 'name': 'Max Mustermann'},
                    {'email': 'john@mail.com', 'name': 'John Doe'}
            ],
            'internal_attendees': [
                    'Administrators',
                    'Reviewers',
                    'Site Administrators',
                    'andreas-ebersbacher',
                    'jan-keller',
                    'werner-wechsler'
            ]
        }

        Important to note is that Groups and Plone users are both listed under
        'internal_attendees' (due to UserAndGroupSelectionWidget), but that
        they must be separated into two groups in the returned dict.
    """
    mtool = getToolByName(context, 'portal_membership')
    gtool = getToolByName(context, 'portal_groups')
    group_ids = gtool.getGroupIds()
    storage = IAttendeesStorage(context)
    new_attendees = {
        'internal_attendees': [],
        'external_attendees': [],
        'groups': [],
        }
    old_names = [k['id'] for k in storage.get('internal_attendees', [])]
    old_groups = [k['name'] for k in storage.get('groups', [])]
    # Groups in the same widget as internal users so is stored under
    # 'internal_attendees'. We'll have to deal with them here...
    for name in data.get('internal_attendees', []):
        if name in group_ids:
            if name in old_groups:
                continue
            # Group
            group = gtool.getGroupById(name)
            new_attendees['groups'].append({'name': group.id})
        elif name not in old_names:
            # User
            member = mtool.getMemberById(name)
            new_attendees['internal_attendees'].append({
                'name': member.getProperty('fullname', None) or member.id,
                'email': member.getProperty('email')
                })

    for entry in data.get('external_attendees', []):
        if entry in storage.get('external_attendees', []):
            continue
        new_attendees['external_attendees'].append(entry)
    return new_attendees

