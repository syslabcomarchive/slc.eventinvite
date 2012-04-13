from zope import interface
from zope import schema
from z3c.form import form as z3cform
from z3c.form import field
from z3c.form import button
from Acquisition import aq_inner
from plone.z3cform.fieldsets.extensible import ExtensibleForm
from plone.z3cform.layout import FormWrapper
from Products.Archetypes.utils import addStatusMessage
from Products.CMFCore.utils import getToolByName
from slc.eventinvite import MessageFactory as _
from slc.eventinvite.adapter import IAttendeesStorage

confirmation_vocabulary= schema.vocabulary.SimpleVocabulary.fromValues(
                                                ['Yes', 'No', 'Maybe'])

class IConfirmAttendanceFormSchema(interface.Interface):
    """ """
    attending = schema.Choice(
                title=_(u"Will you attend this event?"),
                vocabulary=confirmation_vocabulary,
            )

class IConfirmAttendanceFormButtons(interface.Interface):
    """ """
    save = button.Button(title=_(u"Save"))

class ConfirmAttendanceForm(ExtensibleForm, z3cform.Form):
    label = u"Please confirm your attendance."
    ignoreContext = True
    fields = field.Fields(IConfirmAttendanceFormSchema)
    buttons = button.Buttons(IConfirmAttendanceFormButtons)

    @button.handler(IConfirmAttendanceFormButtons['save'])
    def save_confirmation(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = '\n'.join([error.error.__str__() for error in errors])
            return 

        context = aq_inner(self.context)
        mtool = getToolByName(context, 'portal_membership')
        member = mtool.getAuthenticatedMember()
        storage = IAttendeesStorage(context)
        for att in storage.get('internal_attendees', []):   
            if att['id'] == member.id:
                att['attending'] = data['attending']

        addStatusMessage(self.request, 
                        "Thank you for confirming.",
                        type='info')
        self.request.response.redirect(self.context.REQUEST.get('URL'))


class ConfirmAttendance(FormWrapper):
    """ """
    form = ConfirmAttendanceForm 
