import re
from smtplib import SMTPRecipientsRefused
from zope import interface
from zope import schema

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from z3c.form import field
from z3c.form import form as z3cform
from z3c.form import button

from Acquisition import aq_inner

from plone.directives import form

from Products.Archetypes.utils import addStatusMessage
from Products.validation.validators.BaseValidators import EMAIL_RE
from Products.CMFCore.utils import getToolByName

from plone.z3cform.fieldsets.extensible import ExtensibleForm
from plone.z3cform.layout import FormWrapper

from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield import DictRow

from Products.UserAndGroupSelectionWidget.z3cform.widget import \
                                        UsersAndGroupsSelectionFieldWidget

from slc.eventinvite import MessageFactory as _
from slc.eventinvite.adapter import IAttendeesStorage

def isEmail(value):
    if re.match('^'+EMAIL_RE, value):
        return True
    # TODO: collective.z3cform.datagridwidget doesn't catch Invalid, which means we
    # can't provide a nice error message. I don't have time now to check it out
    # and fix it. 
    raise ValueError


class IExternalAttendee(form.Schema):
    """ External attendees are non-Plone users who will be attending the event.
    """
    name = schema.TextLine(
                    title=_(u"Name"),
                    required=True,
                    )

    email = schema.TextLine(
                    title=_(u"Email"), 
                    constraint=isEmail,
                    required=True,
                    )


class IEventInviteFormSchema(interface.Interface):
    """ """
    internal_attendees = schema.List(
                title=_(u"Internal attendees"),
                description=_(u"help_internal_attendees",
                        default=u"Here you can choose attendees "
                        u"from users in this system."),
                value_type=schema.TextLine(),
                required=False,
                missing_value=list(),
            )

    external_attendees = schema.List(
                title=_(u"External attendees"),
                description=_(u"help_external_attendees",
                        default=u"Here you can provide details about attendees "
                        u"who are NOT users of this system."),
                value_type=DictRow(title=u"External Attendee", schema=IExternalAttendee),
                required=False,
                missing_value=list(),
            )


def show_email_new_button(form):
    """ """ 
    context = form.context
    storage = IAttendeesStorage(context)
    attendees = storage.get('internal_attendees', []) + \
                storage.get('external_attendees', [])
    if not attendees:
        return False
    return True


class IEventInviteFormButtons(interface.Interface):
    """ """
    email_all = button.Button(title=_(u"Save and email all attendees"))
    email_new = button.Button(
                    title=_(u"Save and email only the attendees that were added now"),
                    condition=show_email_new_button)


class EventInviteForm(ExtensibleForm, z3cform.Form):
    label = u"Choose the attendees for this event and notify them"
    ignoreContext = True
    fields = field.Fields(IEventInviteFormSchema)
    buttons = button.Buttons(IEventInviteFormButtons)

    def updateFields(self):
        super(EventInviteForm, self).updateFields()
        self.fields['external_attendees'].widgetFactory = DataGridFieldFactory
        self.fields['internal_attendees'].widgetFactory = \
                                            UsersAndGroupsSelectionFieldWidget

    def updateWidgets(self):
        """ Make sure that the widgets are populated with stored or request
            values.
        """
        super(EventInviteForm, self).updateWidgets()
        context = aq_inner(self.context)
        storage = IAttendeesStorage(context)
        for key in ['internal_attendees', 'external_attendees']:
            widget_value = self.request.get('form.widgets.%s' % key)
            if not widget_value:
                widget_value = storage.get(key)
            if widget_value: 
                self.widgets[key].value = widget_value

    def _email_recipients(self, data):
        context = aq_inner(self.context)
        mtool = getToolByName(context, 'portal_membership')
        member = mtool.getAuthenticatedMember()
        host = getToolByName(context, 'MailHost')
        portal_url = getToolByName(context, 'portal_url')
        site = portal_url.getPortalObject()
        email_from_name = site.getProperty('email_from_name')
        email_from_address  = site.getProperty('email_from_address')

        for key in ['internal_attendees', 'external_attendees']:
            mail_template = ViewPageTemplateFile('templates/mail_%s.pt' % key)
            for recipient in data[key]:
                if key == 'internal_attendees':
                    mto = recipient.getProperty('email')
                    recipient = recipient.getProperty('Fullname') or \
                                                            recipient.id
                else:
                    mto = recipient['email']
                    recipient = recipient['name']

                mail_text = mail_template(
                                self,
                                recipient=recipient,
                                sender=member,
                                email_from_name=email_from_name,
                                email_from_address=email_from_address,
                                event=context)
                try:
                    host.send(
                        mail_text, 
                        mto=mto,
                        mfrom=u'%s <%s>' % (email_from_name, email_from_address),
                        subject=_("You have been invited to an event."), 
                        immediate=True
                        )
                except SMTPRecipientsRefused:
                    self.status = \
                        _(u"Error: %s's email address was rejected by the " \
                          u"server." % recipient)


    @button.handler(IEventInviteFormButtons['email_all'])
    def email_all(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = '\n'.join([error.error.__str__() for error in errors])
            return 

        context = aq_inner(self.context)
        storage = IAttendeesStorage(context)
        storage.internal_attendees = data['internal_attendees']
        storage.external_attendees = data['external_attendees']

        self._email_recipients(data)
        addStatusMessage(self.request, 
                        "Attendees have been saved and notified",
                        type='info')
        self.request.response.redirect(self.context.REQUEST.get('URL'))


    @button.handler(IEventInviteFormButtons['email_new'])
    def email_new(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = '\n'.join([error.error.__str__() for error in errors])
            return 

        context = aq_inner(self.context)
        storage = IAttendeesStorage(context)
        new_int_atts = data['internal_attendees'] - storage.internal_attendees
        new_ext_atts = data['external_attendees'] - storage.external_attendees 

        storage.internal_attendees = data['internal_attendees']
        storage.external_attendees = data['external_attendees']

        data['internal_attendees'] = storage.internal_attendees
        data['external_attendees'] = storage.external_attendees

        self._email_recipients(data)
        addStatusMessage(self.request, 
                        "The new attendees have been added and notified.",
                        type='info')
        self.request.response.redirect(self.context.REQUEST.get('URL'))


class EventInvite(FormWrapper):
    """ """
    form = EventInviteForm 

