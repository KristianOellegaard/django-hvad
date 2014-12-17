from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.utils.translation import get_language, ugettext_lazy as _l, ugettext as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.settings import api_settings
from ...utils import set_cached_translation, load_translation

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

#=============================================================================

class TranslationsMixin(object):
    def get_default_field_names(self, *args):
        return (
            super(TranslationsMixin, self).get_default_field_names(*args)
            + [self.Meta.model._meta.translations_accessor]
        )

    def build_field(self, field_name, info, model_class, nested_depth):
        # Force translations being nested and not relational
        if field_name == model_class._meta.translations_accessor:
            class NestedSerializer(serializers.ModelSerializer):
                class Meta:
                    model = model_class._meta.translations_model
                    exclude = ('id', 'master', 'language_code')
                    depth = nested_depth # not -1
                    list_serializer_class = TranslationListSerializer
            return NestedSerializer, {'many': True}
        return super(TranslationsMixin, self).build_field(field_name, info, model_class, nested_depth)

    def save(self, **kwargs):
        creating = (self.instance is None)
        translations = self.validated_data.pop(self.Meta.model._meta.translations_accessor, None)

        if translations is None:
            # happens when partial=True and translations are not set
            instance = super(TranslationsMixin, self).save(**kwargs)
        else:
            arbitrary = translations.popitem()
            kwargs['language_code'] = arbitrary[0]
            kwargs.update(arbitrary[1])
            instance = super(TranslationsMixin, self).save(**kwargs)

            for language, translation in translations.items():
                translation['language_code'] = language
                if creating: # avoid update() looking in the database
                    instance.translate(language)
                self.update(instance, translation)

            if not creating: # get rid of additional translations
                qs = instance._meta.translations_model.objects
                (qs.filter(master=instance)
                   .exclude(language_code__in=(arbitrary[0],)+tuple(translations.keys()))
                   .delete())
        return instance

    def update(self, instance, data):
        'Handle switching to correct translation before actual update'
        enforce = ('language_code' in data)
        language = data.pop('language_code', None) or get_language()
        translation = load_translation(instance, language, enforce=enforce)
        set_cached_translation(instance, translation)

        return super(TranslationsMixin, self).update(instance, data)

#=============================================================================

class TranslatableModelMixin(object):
    default_error_messages = {
        'enforce_violation': _l('Sending a language_code is invalid on serializers '
                                'that enforce a language'),
    }

    def __init__(self, *args, **kwargs):
        try:
            self.language = kwargs.pop('language')
        except KeyError:
            pass
        super(TranslatableModelMixin, self).__init__(*args, **kwargs)

    def get_default_field_names(self, *args):
        return (
            super(TranslatableModelMixin, self).get_default_field_names(*args)
            + list(field.name
                   for field in self.Meta.model._meta.translations_model._meta.fields
                   if field.serialize and not field.name in ('id', 'master'))
        )

    def build_field(self, field_name, info, model_class, nested_depth):
        # Special case the language code field - we handle it manually
        if field_name == 'language_code':
            field = model_class._meta.translations_model._meta.get_field(field_name)
            klass, kwargs = self.build_standard_field(field_name, field)
            kwargs['required'] = False
            return klass, kwargs

        # Try to find a translated field matching the description
        field = None
        if field_name not in ('id', 'master', 'master_id', 'language_code'):
            try:
                field = model_class._meta.translations_model._meta.get_field(field_name)
            except FieldDoesNotExist:
                pass
        if field is not None:
            return self.build_standard_field(field_name, field)

        # Nope, let rest_framework do its usual stuff
        return super(TranslatableModelMixin, self).build_field(
                field_name, info, model_class, nested_depth
        )

    def to_representation(self, instance):
        'Switch language if we are in enforce mode'
        enforce = hasattr(self, 'language')
        language = getattr(self, 'language', None) or get_language()

        translation = load_translation(instance, language, enforce)
        set_cached_translation(instance, translation)

        return super(TranslatableModelMixin, self).to_representation(instance)

    def validate(self, data):
        data = super(TranslatableModelMixin, self).validate(data)
        if hasattr(self, 'language'):
            if 'language_code' in data:
                raise ValidationError(self.error_messages['enforce_violation'])
            data['language_code'] = self.language
        return data

    def update(self, instance, data):
        'Handle switching to correct translation before actual update'
        enforce = 'language_code' in data
        language = data.pop('language_code', None) or get_language()
        translation = load_translation(instance, language, enforce)
        set_cached_translation(instance, translation)

        return super(TranslatableModelMixin, self).update(instance, data)

#=============================================================================

class TranslatableModelSerializer(TranslatableModelMixin, serializers.ModelSerializer):
    pass

class HyperlinkedTranslatableModelSerializer(TranslatableModelMixin,
                                             serializers.HyperlinkedModelSerializer):
    pass
