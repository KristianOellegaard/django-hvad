from django.db import models
from django.utils.translation import ugettext_lazy as _l
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.settings import api_settings

#=============================================================================

class TranslationListSerializer(serializers.ListSerializer):
    'A custom serializer to output translations in a nice dict'
    many = True
    default_error_messages = {
        'not_a_dict': _l('Expected a dictionary of items, but got a {input_type}.'),
    }

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            message = self.error_messages['not_a_dict'].format(
                input_type=type(data).__name__
            )
            raise ValidationError({
                api_settings.NON_FIELD_ERRORS_KEY: [message]
            })

        ret, errors = {}, {}
        for language, translation in data.items():
            try:
                validated = self.child.run_validation(translation)
            except ValidationError as exc:
                errors[language] = exc.detail
            else:
                ret[language] = validated
                errors[language] = {}
        if any(errors.values()):
            raise ValidationError(errors)
        return ret

    def to_representation(self, data):
        iterable = data.all() if isinstance(data, models.Manager) else data
        return dict(
            (item.language_code, self.child.to_representation(item))
            for item in iterable
        )

    def save(self, *args, **kwargs): #pragma: no cover
        raise NotImplementedError('TranslationList must be nested')
    @property
    def data(self): #pragma: no cover
        raise NotImplementedError('TranslationList must be nested')
    @property
    def errors(self): #pragma: no cover
        raise NotImplementedError('TranslationList must be nested')
