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
            return self.__getattr__(attr)
        except AttributeError:
            return default

    def __getattr__(self, key):
        """ """
        context = self.__dict__['context']
        if not IAnnotatable.providedBy(context):
            alsoProvides(context, IAnnotatable)
        annos = IAnnotations(context).get(ANNOTATION_KEY, {})
        if annos.has_key(key): 
            return annos[key]
        raise AttributeError
    
    def __setattr__(self, attr, value):
        """ """
        if not IAnnotatable.providedBy(self.context):
            alsoProvides(self.context, IAnnotatable)
        d = IAnnotations(self.context).get(ANNOTATION_KEY, {})
        d[attr] = value
        IAnnotations(self.context)[ANNOTATION_KEY] = d

