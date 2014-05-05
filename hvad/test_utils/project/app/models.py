from django.db import models
from django.template.defaultfilters import slugify
from hvad.models import TranslatableModel, TranslatedFields


class Normal(TranslatableModel):
    shared_field = models.CharField(max_length=255)
    translations = TranslatedFields(
        translated_field = models.CharField(max_length=255)
    )
    
    def __unicode__(self):
        return self.safe_translation_getter('translated_field', self.shared_field)


class NormalProxy(Normal):

    def __unicode__(self):
        return u'proxied %s' % self.safe_translation_getter('translated_field', self.shared_field)

    class Meta:
        proxy = True


class NormalProxyProxy(NormalProxy):

    def __unicode__(self):
        return u'proxied^2 %s' % self.safe_translation_getter('translated_field', self.shared_field)

    class Meta:
        proxy = True

    
class Related(TranslatableModel):
    normal = models.ForeignKey(Normal, related_name='rel1', null=True)
    
    translated_fields = TranslatedFields(
        translated = models.ForeignKey(Normal, related_name='rel3', null=True),
        translated_to_translated = models.ForeignKey(Normal, related_name='rel4', null=True),
    )

class RelatedProxy(Related):
    class Meta:
        proxy = True

class SimpleRelated(TranslatableModel):
    normal = models.ForeignKey(Normal, related_name='simplerel')
    
    translated_fields = TranslatedFields(
        translated_field = models.CharField(max_length=255),
    )


class SimpleRelatedProxy(SimpleRelated):
    class Meta:
        proxy = True


class Many(models.Model):
    name = models.CharField(max_length=128)
    normals = models.ManyToManyField(Normal, related_name="manyrels")

class Standard(models.Model):
    normal_field = models.CharField(max_length=255)
    normal = models.ForeignKey(Normal, related_name='standards')

class Other(models.Model):
    normal = models.ForeignKey(Normal, related_name='others')
    

class LimitedChoice(models.Model):
    choice_fk = models.ForeignKey(
        Normal,
        limit_choices_to={
            'shared_field__startswith': 'Shared1',
        },
        related_name='limitedchoices_fk'
    )

    choice_mm = models.ManyToManyField(
        Normal,
        limit_choices_to={
            'shared_field__startswith': 'Shared2'
        },
        related_name='limitedchoices_mm'
    )

class Date(TranslatableModel):
    shared_date = models.DateTimeField()
    
    translated_fields = TranslatedFields(
        translated_date = models.DateTimeField()
    )

class AggregateModel(TranslatableModel):
    number = models.IntegerField()
    translated_fields = TranslatedFields(
        translated_number = models.IntegerField(),
    )


class MultipleFields(TranslatableModel):
    first_shared_field = models.CharField(max_length=255)
    second_shared_field = models.CharField(max_length=255)
    translations = TranslatedFields(
        first_translated_field = models.CharField(max_length=255),
        second_translated_field = models.CharField(max_length=255)
    )


class Boolean(TranslatableModel):
    shared_flag = models.BooleanField(default=False)
    translations = TranslatedFields(
        translated_flag = models.BooleanField(default=False)
    )


class AutoPopulated(TranslatableModel):
    slug = models.SlugField(max_length=255, blank=True)
    translations = TranslatedFields(
        translated_name = models.CharField(max_length=255)
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.translated_name[:125])
        super(AutoPopulated, self).save(*args, **kwargs)


