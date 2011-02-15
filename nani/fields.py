from django.db.models.fields.related import (ForeignKey, 
    ReverseSingleRelatedObjectDescriptor)
from nani.utils import get_cached_translation, combine


class ReverseTranslatedSingleRelatedObjectDescriptor(ReverseSingleRelatedObjectDescriptor):
    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError("%s must be accessed via instance" % self._field.name)
        value = get_cached_translation(value)
        super(ReverseTranslatedSingleRelatedObjectDescriptor, self).__set__(instance, value)
        
    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self
        value = super(ReverseTranslatedSingleRelatedObjectDescriptor, self).__get__(instance, instance_type)
        return combine(value)


class TranslatedForeignKey(ForeignKey):
    def __init__(self, to, *args, **kwargs):
        self._to = to
        to = to._meta.translations_model
        super(TranslatedForeignKey, self).__init__(to, *args, **kwargs)

    def contribute_to_class(self, cls, name):
        super(ForeignKey, self).contribute_to_class(cls, name)
        setattr(cls, self.name, ReverseTranslatedSingleRelatedObjectDescriptor(self))
        if isinstance(self.rel.to, basestring):
            target = self.rel.to
        else:
            target = self.rel.to._meta.db_table
        cls._meta.duplicate_targets[self.column] = (target, "o2m")

    def contribute_to_related_class(self, cls, related):
        super(TranslatedForeignKey, self).contribute_to_related_class(self._to, related)