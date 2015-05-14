import django
from django.db import models
from django.template.defaultfilters import slugify
from hvad.models import TranslatableModel, TranslatedFields
from hvad.manager import TranslationManager, TranslationQueryset
from hvad.utils import get_cached_translation
from django.utils.encoding import python_2_unicode_compatible

#===============================================================================
# Basic models

@python_2_unicode_compatible
class Normal(TranslatableModel):
    shared_field = models.CharField(max_length=255)
    translations = TranslatedFields(
        translated_field = models.CharField(max_length=255)
    )

    def __str__(self):
        return self.safe_translation_getter('translated_field', self.shared_field)

@python_2_unicode_compatible
class Unique(TranslatableModel):
    shared_field = models.CharField(max_length=255, unique=True)
    translations = TranslatedFields(
        translated_field = models.CharField(max_length=255, unique=True)
    )

    def __str__(self):
        return self.safe_translation_getter('translated_field', self.shared_field)

@python_2_unicode_compatible
class NormalProxy(Normal):
    def __str__(self):
        return u'proxied %s' % super(NormalProxy, self).__str__()

    class Meta:
        proxy = True

@python_2_unicode_compatible
class NormalProxyProxy(NormalProxy):
    def __str__(self):
        return u'proxied^2 %s' % super(NormalProxyProxy, self).__str__()

    class Meta:
        proxy = True

#===============================================================================
# Models for testing relations

class Related(TranslatableModel):
    """ Model with foreign keys to Normal, both shared and translatable """
    normal = models.ForeignKey(Normal, related_name='rel1', null=True)
    translated_fields = TranslatedFields(
        translated = models.ForeignKey(Normal, related_name='rel3', null=True),
        translated_to_translated = models.ForeignKey(Normal, related_name='rel4', null=True),
    )

class RelatedProxy(Related):
    """ Proxy to model with foreign keys to Normal, both shared and translatable """
    class Meta:
        proxy = True


class SimpleRelated(TranslatableModel):
    """ Model with foreign key to Normal, shared only and regular translatable field """
    normal = models.ForeignKey(Normal, related_name='simplerel')
    manynormals = models.ManyToManyField(Normal, blank=True, related_name='manysimplerel')
    translated_fields = TranslatedFields(
        translated_field = models.CharField(max_length=255),
    )

class SimpleRelatedProxy(SimpleRelated):
    """ Proxy to model with foreign key to Normal, shared only and regular translatable field """
    class Meta:
        proxy = True


class RelatedRelated(TranslatableModel):
    """ Model with foreign keys to Related and SimpleRelated, both shared and transltable.
        This is used to test deep relations to Normal
    """
    related = models.ForeignKey(Related, related_name='+', null=True)
    simple = models.ForeignKey(SimpleRelated, related_name='+', null=True)

    translated_fields = TranslatedFields(
        trans_related = models.ForeignKey(Related, related_name='+', null=True),
        trans_simple = models.ForeignKey(SimpleRelated, related_name='+', null=True),
    )


@python_2_unicode_compatible
class Many(models.Model):
    """ Untranslatable Model with M2M key to Normal """
    name = models.CharField(max_length=128)
    normals = models.ManyToManyField(Normal, related_name="manyrels")

    def __str__(self):
        return self.name


class Standard(models.Model):
    """ Untranslatable Model with foreign key to Normal """
    normal_field = models.CharField(max_length=255)
    normal = models.ForeignKey(Normal, related_name='standards')
    date = models.ForeignKey('Date', null=True, related_name='standards')


class StandardRelated(TranslatableModel):
    """ Translatable mode with foreign key to untranslatable """
    shared_field = models.CharField(max_length=255)
    standard = models.ForeignKey(Standard, related_name='related')
    translations = TranslatedFields(
        translated_field = models.CharField(max_length=255),
    )


class FullTranslationManager(TranslationManager):
    use_for_related_fields = True
    default_class = TranslationQueryset

class QONormal(TranslatableModel):
    shared_field = models.CharField(max_length=255)
    translations = TranslatedFields(
        translated_field = models.CharField(max_length=255)
    )
    objects = FullTranslationManager()

class QOSimpleRelated(TranslatableModel):
    normal = models.ForeignKey(QONormal, related_name='simplerel', null=True)
    translations = TranslatedFields(
        translated_field = models.CharField(max_length=255),
    )
    objects = FullTranslationManager()

class QOMany(TranslatableModel):
    normals = models.ManyToManyField(QONormal, related_name="manyrels")
    translations = TranslatedFields(
        translated_field = models.CharField(max_length=255),
    )
    objects = FullTranslationManager()


#===============================================================================
# Models for testing abstract model support
#
# This creates an abstract hierarchy like this:
#
# AbstractA
#     |
# AbstractAA      AbstractB
#     \_______________/
#             |
#         ConcreteAB
#             |
#      ConcreteABProxy

class AbstractA(TranslatableModel):
    translations = TranslatedFields(
        translated_field_a = models.ForeignKey(Normal, related_name='%(class)s_set'),
    )
    class Meta:
        abstract = True

class AbstractAA(AbstractA):
    shared_field_a = models.CharField(max_length=255)
    class Meta:
        abstract = True

class AbstractB(TranslatableModel):
    shared_field_b = models.ForeignKey(Normal, related_name='%(class)s_set')
    translations = TranslatedFields(
        translated_field_b = models.CharField(max_length=255),
    )
    class Meta:
        abstract = True

@python_2_unicode_compatible
class ConcreteAB(AbstractAA, AbstractB):
    shared_field_ab = models.CharField(max_length=255)
    translations = TranslatedFields(
        translated_field_ab = models.CharField(max_length=255),
    )

    def __str__(self):
        return '%s, %s, %s' % (
            str(self.safe_translation_getter('translated_field_a', self.shared_field_a)),
            self.safe_translation_getter('translated_field_b', str(self.shared_field_b)),
            self.safe_translation_getter('translated_field_ab', self.shared_field_ab),
        )

@python_2_unicode_compatible
class ConcreteABProxy(ConcreteAB):
    def __str__(self):
        return 'proxied %s, %s, %s' % (
            str(self.safe_translation_getter('translated_field_a', self.shared_field_a)),
            self.safe_translation_getter('translated_field_b', str(self.shared_field_b)),
            self.safe_translation_getter('translated_field_ab', self.shared_field_ab),
        )
    class Meta:
        proxy = True

#===============================================================================
# Models for testing admin module

@python_2_unicode_compatible
class AdvancedAdminModel(TranslatableModel):
    shared = models.CharField(max_length=255)
    time_field = models.DateTimeField()
    translations = TranslatedFields(
        translated = models.CharField(max_length=255),
        translated_ro = models.CharField(max_length=255),
        translated_hidden = models.CharField(max_length=255),
        translated_rel = models.ForeignKey(Normal, related_name='+', null=True),
    )

    def __str__(self):
        shared = '%s / %s' % (
            self.shared, self.time_field,
        )
        if get_cached_translation(self) is None:
            translated = '[none]'
        else:
            translated = '%s / %s / %s [%s]' % (
                self.translated,
                self.translated_ro,
                self.translated_hidden,
                self.language_code,
            )
        return '%s / %s' % (shared, translated)


#===============================================================================
# Models for testing choice limiting in foreign keys

class LimitedChoice(models.Model):
    choice_fk = models.ForeignKey(Normal,
        limit_choices_to={'shared_field__startswith': 'Shared1',},
        related_name='limitedchoices_fk',
    )
    choice_mm = models.ManyToManyField(Normal,
        limit_choices_to={'shared_field__startswith': 'Shared2',},
        related_name='limitedchoices_mm',
    )

#===============================================================================
# Model for testing miscellaneous data and query types

class Date(TranslatableModel):
    """ Model for testing Date manipulation """
    shared_date = models.DateTimeField()
    translated_fields = TranslatedFields(
        translated_date = models.DateTimeField()
    )

    class Meta:
        get_latest_by = 'shared_date'

#===============================================================================

class AggregateModel(TranslatableModel):
    """ Model for testing queryset aggregation """
    number = models.IntegerField()
    translated_fields = TranslatedFields(
        translated_number = models.IntegerField(),
    )


class MultipleFields(TranslatableModel):
    """ Model for testing multi-field queries """
    first_shared_field = models.CharField(max_length=255)
    second_shared_field = models.CharField(max_length=255)
    translations = TranslatedFields(
        first_translated_field = models.CharField(max_length=255),
        second_translated_field = models.CharField(max_length=255)
    )


class Boolean(TranslatableModel):
    """ Model for testing boolean data manipulation """
    shared_flag = models.BooleanField(default=False)
    translations = TranslatedFields(
        translated_flag = models.BooleanField(default=False)
    )


class AutoPopulated(TranslatableModel):
    """ Model for testing custom save method """
    translations = TranslatedFields(
        slug = models.SlugField(max_length=255, blank=True),
        translated_name = models.CharField(max_length=255),
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.translated_name[:125])
        super(AutoPopulated, self).save(*args, **kwargs)
