from django.http import Http404
from django.views.generic.edit import UpdateView
from admin import TranslatableModelAdminMixin
from forms import translatable_modelform_factory, TranslatableModelForm
from utils import collect_context_modifiers

class TranslatableBaseView(UpdateView, TranslatableModelAdminMixin):
    form_class = TranslatableModelForm


    def filter_kwargs(self):
        """
        ORM Lookup kwargs from URL pattern
        Default {'pk': 'object_id'}

        Syntax:
        - {'model_attr': 'url_block_name'}
        """
        if self.kwargs.has_key("slug"):
            return {self.slug_field: self.kwargs["slug"]}
        return {'pk': self.kwargs['object_id']}

    def get_form_class(self):
        language = self._language(self.request)
        return translatable_modelform_factory(language, self.model, form=self.form_class)

    def get_queryset(self):
        if self.queryset is None:
            if self.model:
                language = self._language(self.request)
                return self.model._default_manager.language(language)

    def _get_object(self, queryset=None):
        if not queryset:
            queryset = self.get_queryset()
        model = self.model
        try:
            obj = queryset.get(**self.filter_kwargs())
        except self.model.DoesNotExist:
            obj = None
        if obj:
            return obj
        queryset = self.model.objects.untranslated()
        try:
            obj = queryset.get(**self.filter_kwargs())
        except model.DoesNotExist:
            return None
        new_translation = model._meta.translations_model()
        new_translation.language_code = self._language(self.request)
        new_translation.master = obj
        setattr(obj, model._meta.translations_cache, new_translation)
        return obj

    def context_modifier_languages_available(self, **kwargs):
        context = {
            'language_tabs': self.get_language_tabs(self.request, self.get_available_languages(self.object))
        }
        return context

    def get_context_data(self, **kwargs):
        context = super(TranslatableBaseView, self).get_context_data(**kwargs)
        context.update(collect_context_modifiers(self, extra_kwargs=kwargs))
        return context

class TranslatableCreateView(TranslatableBaseView, TranslatableModelAdminMixin):
    """
    Untested, use with caution - or write tests if you see this :-)
    """
    pass

class TranslatableUpdateView(TranslatableBaseView, TranslatableModelAdminMixin):
    """
    A generic class based update view for translatable models.
    """
    def get_object(self, queryset=None):
        obj = self._get_object(queryset)
        if not obj:
            raise Http404("%s instance with arguments %s does not exist" % (self.model, self.filter_kwargs()))
        return obj

