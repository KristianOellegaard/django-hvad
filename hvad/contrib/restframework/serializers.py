import django
from django.db.models.fields import FieldDoesNotExist
from django.utils.translation import get_language, ugettext_lazy as _l
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from hvad.exceptions import WrongManager
from hvad.utils import get_cached_translation, set_cached_translation, load_translation
from hvad.contrib.restframework.utils import TranslationListSerializer
from collections import OrderedDict

veto_fields = ('id', 'master')


#=============================================================================

class NestedTranslationSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        """ Nested serializer gets the full object, but some field serializers need the
            actual model their data lives in, that is, the translation. We detect it here. """
        translation = get_cached_translation(instance)
        ret = OrderedDict()
        for field in self._readable_fields:
            try:
                try:
                    attribute = field.get_attribute(instance)
                except (WrongManager, FieldDoesNotExist):
                    attribute = field.get_attribute(translation)
            except SkipField:
                continue
            if attribute is None:
                ret[field.field_name] = None
            else:
                ret[field.field_name] = field.to_representation(attribute)
        return ret


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
            BaseSerializer = getattr(self.Meta, 'translations_serializer', NestedTranslationSerializer)
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

    def create(self, data):
        accessor = self.Meta.model._meta.translations_accessor
        translations_data = data.pop(accessor, None)
        if translations_data:
            arbitrary = translations_data.popitem()
            data.update(arbitrary[1])
            data['language_code'] = arbitrary[0]
            instance = super(TranslationsMixin, self).create(data)

            for language, translation_data in translations_data.items():
                instance.translate(language)
                self.update_translation(instance, translation_data)
        else:
            instance = super(TranslationsMixin, self).create(data)
        return instance

    def update(self, instance, data):
        accessor = self.Meta.model._meta.translations_accessor
        translations_data = data.pop(accessor, None)
        if translations_data:
            arbitrary = translations_data.popitem()
            data.update(arbitrary[1])
            stashed = set_cached_translation(
                instance, load_translation(instance, arbitrary[0], enforce=True)
            )
            instance = super(TranslationsMixin, self).update(instance, data)

            for language, translation_data in translations_data.items():
                set_cached_translation(instance, load_translation(instance, language, enforce=True))
                self.update_translation(instance, translation_data)

            set_cached_translation(instance, stashed)
            qs = instance._meta.translations_model.objects
            (qs.filter(master=instance)
                .exclude(language_code__in=(arbitrary[0],)+tuple(translations_data.keys()))
                .delete())
        else:
            instance = super(TranslationsMixin, self).update(instance, data)
        return instance

    def update_translation(self, instance, data):
        if django.VERSION >= (1, 8):
            fields = set(field.name
                         for field in self.Meta.model._meta.translations_model._meta.get_fields()
                         if not field.is_relation or                    # regular fields are ok
                            field.one_to_one or                         # one to one is ok
                            field.many_to_one and field.related_model)  # many_to_one only if not generic
        else:
            fields = set(name
                         for name in self.Meta.model._meta.translations_model._meta.get_all_field_names())
        fields.intersection_update(data)
        vetoed = fields.intersection('id', 'master', 'master_id', 'language_code')
        if vetoed:
            raise KeyError('These fields are not allowed in data: ' % ', '.join(vetoed))

        for key, value in data.items():
            setattr(instance, key, value)
        instance.save(update_fields=fields)

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
