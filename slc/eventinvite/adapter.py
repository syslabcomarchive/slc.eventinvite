from zope.annotation.interfaces import IAnnotatable, IAnnotations
from zope.interface import Interface
from zope.interface import alsoProvides
from zope.interface import implements

ANNOTATION_KEY = 'slc.eventinvite'

class IAttendeesStorage(Interface):
    """ """

class AttendeesStorage(object):
    """ """
    implements(IAttendeesStorage)

    def __init__(self, context):
        """ """
        self.__dict__['context'] = context

    def get(self, attr, default=None):
        try:
            return self.__get__(attr)
        except AttributeError:
            return default

    def __get__(self, attr):
        """ """
        if not IAnnotatable.providedBy(self.context):
            alsoProvides(self.context, IAnnotatable)

        annos = IAnnotations(self.context).get(ANNOTATION_KEY, {})
        if annos.get(attr): 
            return annos[attr]
        raise AttributeError
    
    def __setattr__(self, attr, value):
        """ """
        if not IAnnotatable.providedBy(self.context):
            alsoProvides(self.context, IAnnotatable)

        if IAnnotations(self.context).has_key(ANNOTATION_KEY):
            IAnnotations(self.context)[ANNOTATION_KEY] = {attr: value}
        else:
            IAnnotations(self.context)[ANNOTATION_KEY][attr] = value

