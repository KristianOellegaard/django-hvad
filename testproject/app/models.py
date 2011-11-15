from django.db import models
from nani.models import TranslatableModel, TranslatedFields


class Normal(TranslatableModel):
    shared_field = models.CharField(max_length=255)
    translations = TranslatedFields(
        translated_field = models.CharField(max_length=255)
    )
    
    def __unicode__(self):
        return self.safe_translation_getter('translated_field', self.shared_field)

    
class Related(TranslatableModel):
    normal = models.ForeignKey(Normal, related_name='rel1', null=True)
    
    translated_fields = TranslatedFields(
        translated = models.ForeignKey(Normal, related_name='rel3', null=True),
        translated_to_translated = models.ForeignKey(Normal, related_name='rel4', null=True),
    )


class SimpleRelated(TranslatableModel):
    normal = models.ForeignKey(Normal, related_name='simplerel')
    
    translated_fields = TranslatedFields(
        translated_field = models.CharField(max_length=255),
    )


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
