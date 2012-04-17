import re
from zope import interface
from zope import schema

from z3c.form import field
from z3c.form import form as z3cform
from z3c.form import button

from Acquisition import aq_inner

from plone.directives import form

from Products.Archetypes.utils import addStatusMessage
from Products.validation.validators.BaseValidators import EMAIL_RE

from plone.z3cform.fieldsets.extensible import ExtensibleForm
from plone.z3cform.layout import FormWrapper

from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield import DictRow

from Products.UserAndGroupSelectionWidget.z3cform.widget import \
                                        UsersAndGroupsSelectionFieldWidget

from slc.eventinvite import MessageFactory as _
from slc.eventinvite import utils 
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
                if key == 'internal_attendees':
                    widget_value = [k['id'] for k in storage.get(key, [])]
                else:
                    widget_value = storage.get(key)
            if widget_value: 
                self.widgets[key].value = widget_value

    @button.handler(IEventInviteFormButtons['email_all'])
    def email_all(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = '\n'.join([error.error.__str__() for error in errors])
            return 
        data = utils.save_attendees(self.context, data)
        utils.email_recipients(self.context, data)
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
        new_attendees = utils.get_new_attendees(context, data)
        utils.save_attendees(context, data)
        utils.email_recipients(context, new_attendees)
        if new_attendees['internal_attendees'] or \
                new_attendees['external_attendees']:
            addStatusMessage(self.request, 
                            "The new attendees have been added and notified.",
                            type='info')
        self.request.response.redirect(self.context.REQUEST.get('URL'))


class EventInvite(FormWrapper):
    """ """
    form = EventInviteForm 

