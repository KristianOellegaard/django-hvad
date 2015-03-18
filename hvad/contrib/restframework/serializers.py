from django.db.models.fields import FieldDoesNotExist
from django.utils.translation import get_language, ugettext_lazy as _l
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from ...utils import set_cached_translation, load_translation
from .utils import TranslationListSerializer

veto_fields = ('id', 'master')


#=============================================================================

class TranslationsMixin(object):
    ''' Adds support for nested translations in a serializer
        Generated field will default to the model's translation accessor.
    '''

    # Add the translations accessor to default serializer fields
    def get_default_field_names(self, *args):
        return (
            super(TranslationsMixin, self).get_default_field_names(*args)
            + [self.Meta.model._meta.translations_accessor]
        )

    def build_field(self, field_name, info, model_class, nested_depth):
        # Special handling for translations field so it is nested and not relational
        if field_name == model_class._meta.translations_accessor:
            # Create a nested serializer as a subclass of configured translations_serializer
            BaseSerializer = getattr(self.Meta, 'translations_serializer', serializers.ModelSerializer)
            BaseMeta = getattr(BaseSerializer, 'Meta', None)
            exclude = veto_fields + ('language_code',)
            if BaseMeta is not None:
                exclude += tuple(getattr(BaseMeta, 'exclude', ()))

            NestedMeta = type('Meta', (object,) if BaseMeta is None else (BaseMeta, object), {
                'model': model_class._meta.translations_model,
                'exclude': exclude,
                'depth': nested_depth,
                'list_serializer_class': TranslationListSerializer,
            })
            NestedSerializer = type('NestedSerializer', (BaseSerializer,), {'Meta': NestedMeta})

            kwargs = {'many': True}
            if isinstance(self, TranslatableModelMixin):
                kwargs['required'] = False
            return NestedSerializer, kwargs

        return super(TranslationsMixin, self).build_field(field_name, info, model_class, nested_depth)

    def to_internal_value(self, data):
        # Allow TranslationsMixin to be combined with TranslatableModelSerializer
        # This means we allow translated fields to be absent if translations are set

        if isinstance(self, TranslatableModelMixin):
            tmodel = self.Meta.model._meta.translations_model

            # Look for translated fields, and mark them read_only if translations is set
            if self.Meta.model._meta.translations_accessor in data:
                for name, field in self.fields.items():
                    source = field.source or field.field_name
                    if source in veto_fields:
                        continue # not a translated field
                    try:
                        tmodel._meta.get_field(source)
                    except FieldDoesNotExist:
                        continue # not a translated field
                    field.read_only = True

        return super(TranslationsMixin, self).to_internal_value(data)

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
        stashed = set_cached_translation(instance, translation)

        result = super(TranslationsMixin, self).update(instance, data)
        set_cached_translation(instance, stashed)
        return result

#=============================================================================

class TranslatableModelMixin(object):
    ''' Adds support for translated fields on a serializer '''
    default_error_messages = {
        'enforce_violation': _l('Sending a language_code is invalid on serializers '
                                'that enforce a language'),
    }

    def __init__(self, *args, **kwargs):
        # We use an exception because None is a valid value for language
        try:
            self.language = kwargs.pop('language')
        except KeyError:
            pass
        super(TranslatableModelMixin, self).__init__(*args, **kwargs)

    def get_default_field_names(self, *args):
        # Add translated fields into default field names
        return (
            super(TranslatableModelMixin, self).get_default_field_names(*args)
            + list(field.name
                   for field in self.Meta.model._meta.translations_model._meta.fields
                   if field.serialize and not field.name in veto_fields)
        )

    def get_uniqueness_extra_kwargs(self, field_names, declared_fields, *args):
        # Default implementation chokes on translated fields, filter them out
        shared_fields = []
        for field_name in field_names:
            field = declared_fields.get(field_name)
            if field is not None:
                field_name = field.source or field_name
            if field_name not in veto_fields:
                try:
                    self.Meta.model._meta.translations_model._meta.get_field(field_name)
                except FieldDoesNotExist:
                    pass
                else:
                    continue
            shared_fields.append(field_name)

        return super(TranslatableModelMixin, self).get_uniqueness_extra_kwargs(shared_fields, declared_fields, *args)

    def build_field(self, field_name, info, model_class, nested_depth):
        # Special case the language code field - we handle it manually
        if field_name == 'language_code':
            field = model_class._meta.translations_model._meta.get_field(field_name)
            klass, kwargs = self.build_standard_field(field_name, field)
            kwargs['required'] = False
            return klass, kwargs

        # Try to find a translated field matching the description
        field = None
        if field_name not in veto_fields:
            try:
                field = model_class._meta.translations_model._meta.get_field(field_name)
            except FieldDoesNotExist:
                pass
        if field is not None:
            return self.build_standard_field(field_name, field)

        # Nothing unusual, let rest_framework do its stuff
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
