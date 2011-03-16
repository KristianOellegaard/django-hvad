from django.db import models
from nani.fields import TranslatedForeignKey
from nani.models import TranslateableModel, TranslatedFields

class Normal(TranslateableModel):
    shared_field = models.CharField(max_length=255)
    translations = TranslatedFields(
        translated_field = models.CharField(max_length=255)
    )
    
    def __unicode__(self):
        return self.safe_getter('translated_field', self.shared_field)

    
class Related(TranslateableModel):
    normal = models.ForeignKey(Normal, related_name='rel1', null=True)
    normal_trans = TranslatedForeignKey(Normal, related_name='rel2', null=True)
    
    translated_fields = TranslatedFields(
        translated = models.ForeignKey(Normal, related_name='rel3', null=True),
        translated_to_translated = models.ForeignKey(Normal, related_name='rel4', null=True),
    )

class Standard(models.Model):
    normal_field = models.CharField(max_length=255)
    normal = models.ForeignKey(Normal, related_name='standards')
    

class Date(TranslateableModel):
    shared_date = models.DateTimeField()
    
    translated_fields = TranslatedFields(
        translated_date = models.DateTimeField()
    )