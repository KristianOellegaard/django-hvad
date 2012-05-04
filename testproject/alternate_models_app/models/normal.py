from django.db import models
from hvad.models import TranslatableModel, TranslatedFields


class NormalAlternate(TranslatableModel):
    shared_field = models.CharField(max_length=255)
    translations = TranslatedFields(
        translated_field = models.CharField(max_length=255)
    )
    
    def __unicode__(self):
        return self.safe_translation_getter('translated_field', self.shared_field)
    
    class Meta:
        app_label = "alternate_models_app"
