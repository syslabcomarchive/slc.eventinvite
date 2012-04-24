from zope import interface
from zope import schema
from z3c.form import form as z3cform
from z3c.form import field
from z3c.form import button
from Acquisition import aq_inner
from zExceptions import NotFound
from plone.z3cform.fieldsets.extensible import ExtensibleForm
from plone.z3cform.layout import FormWrapper
from Products.Archetypes.utils import addStatusMessage
from slc.eventinvite import MessageFactory as _
from slc.eventinvite import utils
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
    save = button.Button(title=_(u"Confirm"))

class ConfirmAttendanceForm(ExtensibleForm, z3cform.Form):
    ignoreContext = True
    fields = field.Fields(IConfirmAttendanceFormSchema)
    buttons = button.Buttons(IConfirmAttendanceFormButtons)

    @property
    def label(self):
        return u"Confirm attendance: %s" % self.context.Title()

    def updateWidgets(self):
        """ If a user already confirmed, we want to reflect that in the default
            value.
        """
        super(ConfirmAttendanceForm, self).updateWidgets()
        context = aq_inner(self.context)
        storage = IAttendeesStorage(context)
        self.widgets['attending'].value = utils.get_confirmation(context)


    @button.handler(IConfirmAttendanceFormButtons['save'])
    def save_confirmation(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = '\n'.join([error.error.__str__() for error in errors])
            return 
        context = aq_inner(self.context)
        utils.save_confirmation(context, data['attending'])
        addStatusMessage(self.request, 
                        "Thank you for confirming.", type='info')
        self.request.response.redirect(self.context.REQUEST.get('URL'))


class ConfirmAttendance(FormWrapper):
    """ """
    form = ConfirmAttendanceForm 

    def __call__(self, **kw):
        """ Check whether the current user was invited. If not we return a 404.
        """
        if not self.is_user_invited(self.context):
            raise NotFound
        return super(ConfirmAttendance, self).__call__(**kw)

