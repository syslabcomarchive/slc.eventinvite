import logging
from smtplib import SMTPRecipientsRefused
from zope import component
from Products.CMFCore.utils import getToolByName
from slc.eventinvite.adapter import IAttendeesStorage
from slc.eventinvite import MessageFactory as _

log = logging.getLogger(__name__)

def is_invited(event):
    """ Check whether the current user is invited to the event.
    """
    mtool = getToolByName(event, 'portal_membership')
    member = mtool.getAuthenticatedMember()
    if member.id not in get_invited_usernames(event):
        member_groups = member.getGroups()
        if not member_groups:
            return False
        all_invited_groups = get_invited_groups(event)
        invited_groups = [g for g in member_groups if g in all_invited_groups]
        if not invited_groups:
            return False
    return True

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
                'attending': {'Yes':[], 'No':[], 'Maybe':[]}, 
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


def get_invited_groups(context):
    storage = IAttendeesStorage(context)
    return [g['name'] for g in storage.get('groups', [])]

def get_invited_usernames(context):
    storage = IAttendeesStorage(context)
    return [m['id'] for m in storage.get('internal_attendees', [])]


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


def save_confirmation(context, confirmation):
    mtool = getToolByName(context, 'portal_membership')
    gtool = getToolByName(context, 'portal_groups')
    storage = IAttendeesStorage(context)
    member = mtool.getAuthenticatedMember()
    # If the user belongs to any invited groups, store the user's confirmation
    # for those groups.
    member_groups = member.getGroups()
    if 'AuthenticatedUsers' in member_groups:
        member_groups.remove('AuthenticatedUsers')
    if member_groups:
        group_dicts = storage.groups
        invited_groups = get_invited_groups(context)
        groups_to_confirm = [g for g in member_groups if g in invited_groups]
        for group in groups_to_confirm:
            for group_dict in group_dicts:
                if group_dict['name'] == group:
                    group_dict['attending'][confirmation].append({
                        'name': member.getProperty('fullname', None) or member.id,
                        'email': member.getProperty('email'),
                        'id': member.id,
                    })
                    break
        storage.groups = group_dicts
    
    # If the user was (also) invited individually, store the confirmation under
    # internal_attendees
    if member.id in get_invited_usernames(context):
        internal_attendees = storage.get('internal_attendees', [])
        for att in internal_attendees:   
            if att['id'] == member.id:
                att['attending'] = confirmation 
        storage.internal_attendees = internal_attendees


def get_confirmation(context):
    mtool = getToolByName(context, 'portal_membership')
    member = mtool.getAuthenticatedMember()
    storage = IAttendeesStorage(context)
    # See if user was invited individually
    invited_usernames = get_invited_usernames(context)
    if member.id in invited_usernames: 
        index = invited_usernames.index(member.id)
        return storage.internal_attendees[index].get('attending', None)
    # Get the first invited group that the user belongs to and return his
    # confirmation status.
    member_groups = member.getGroups()
    all_invited_groups = get_invited_groups(context)
    invited_groups = [g for g in member_groups if g in all_invited_groups]
    if invited_groups:
        invited_group = invited_groups[0]
        group_status = storage.groups
        for group in group_status:
            if group['name'] == invited_group:
                if member.id in [x['id'] for x in group['attending']['Yes']]:
                    return 'Yes'
                elif member.id in [x['id'] for x in group['attending']['No']]:
                    return 'No'
                elif member.id in [x['id'] for x in group['attending']['Maybe']]:
                    return 'Maybe'
    
