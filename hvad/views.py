from django.views.generic.detail import SingleObjectMixin, SingleObjectTemplateResponseMixin
from django.views.generic.edit import ModelFormMixin, ProcessFormView, BaseDeleteView
from django.utils.translation import get_language
from .forms import translatable_modelform_factory
from .utils import collect_context_modifiers
import warnings

class _TransitionObjectMixin(SingleObjectMixin):
    def get_object(self, queryset=None):
        _get_object = getattr(self, '_get_object', None)
        if callable(_get_object):
            # raise in 1.3, remove in 1.5
            warnings.warn('Method \'_get_object()\' is deprecated and will be removed. '
                          'Please update view %s to use \'get_object()\' instead.'
                          % self.__class__.__name__, DeprecationWarning)
            return _get_object(queryset)

        filter_kwargs = getattr(self, 'filter_kwargs', None)
        if callable(filter_kwargs):
            # raise in 1.3, remove in 1.5
            warnings.warn('Method \'filter_kwargs()\' is deprecated and will be removed. '
                          'Please update view %s to use \'get_queryset()\' or '
                          '\'get_object()\'.' % self.__class__.__name__,
                          DeprecationWarning)
            if queryset is None:
                queryset = self.get_queryset()
            return queryset.get(**filter_kwargs())

        elif (self.pk_url_kwarg == 'pk' and 'object_id' in self.kwargs and 'pk' not in self.kwargs):
            # raise in 1.3, remove in 1.5
            warnings.warn('Default view argument for pk has changed from \'object_id\' '
                          'to \'pk\'. Please update view %s.' % self.__class__.__name__,
                          DeprecationWarning)
            self.kwargs['pk'] = self.kwargs['object_id']

        return super(_TransitionObjectMixin, self).get_object(queryset)


class TranslatableModelFormMixin(ModelFormMixin, _TransitionObjectMixin):
    ''' ModelFormMixin that works with an TranslatableModelForm in **enforce** mode '''
    query_language_key = 'language'

    def get_language(self):
        legacy = getattr(self, '_language', None)
        if callable(legacy):
            # raise in 1.3, remove in 1.5
            warnings.warn('Method \'_language\' has been renamed to \'get_language()\'. '
                          'Please update view %s.' % self.__class__.__name__,
                          DeprecationWarning)
            return legacy(self.request)
        return self.request.GET.get(self.query_language_key) or get_language()

    def get_form_class(self):
        if self.model is not None:
            model = self.model
        elif getattr(self, 'object', None) is not None:
            model = self.object.__class__
        else:
            qs = self.get_queryset()
            model = getattr(qs, 'shared_model', qs.model)

        kwargs = {}
        if self.form_class is not None:
            kwargs['form'] = self.form_class
        return translatable_modelform_factory(self.get_language(), model, **kwargs)

    def get_context_data(self, **kwargs):
        # Deprecation warning is triggered inside collect_context_modifiers
        # remove this in 1.5
        context = super(TranslatableModelFormMixin, self).get_context_data(**kwargs)
        context.update(collect_context_modifiers(self, extra_kwargs=kwargs))
        return context

#=============================================================================

class TranslatableBaseCreateView(TranslatableModelFormMixin, ProcessFormView):
    def get(self, request, *args, **kwargs):
        self.object = None
        return super(TranslatableBaseCreateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = None
        return super(TranslatableBaseCreateView, self).post(request, *args, **kwargs)

class TranslatableCreateView(SingleObjectTemplateResponseMixin, TranslatableBaseCreateView):
    template_name_suffix = '_form'

#-------------------------------------------------------------------------

class TranslatableBaseUpdateView(TranslatableModelFormMixin, ProcessFormView):
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(TranslatableBaseUpdateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(TranslatableBaseUpdateView, self).post(request, *args, **kwargs)

class TranslatableUpdateView(SingleObjectTemplateResponseMixin, TranslatableBaseUpdateView):
    template_name_suffix = '_form'

#-------------------------------------------------------------------------

class TranslatableBaseDeleteView(BaseDeleteView, _TransitionObjectMixin):
    pass

class TranslatableDeleteView(SingleObjectTemplateResponseMixin, TranslatableBaseDeleteView):
    template_name_suffix = '_confirm_delete'

#=============================================================================
#=============================================================================
#=============================================================================

from django.views.generic.edit import UpdateView
from .admin import TranslatableModelAdminMixin
from .forms import TranslatableModelForm

class TranslatableBaseView(UpdateView, TranslatableModelAdminMixin): #pragma: no cover
    form_class = TranslatableModelForm

    def __init__(self, *args, **kwargs):
        warnings.warn('TranslatableBaseView is deprecated and will be removed '
                      'in release 1.3. Please update %s to use new Django-compliant '
                      'views instead.' % self.__class__.__name__,
                      DeprecationWarning, stacklevel=2)
        super(TranslatableBaseView, self).__init__(*args, **kwargs)

    def filter_kwargs(self):
        if "slug" in self.kwargs:
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
        if queryset is None:
            queryset = self.get_queryset()
        model = self.model
        try:
            obj = queryset.get(**self.filter_kwargs())
        except self.model.DoesNotExist:
            obj = None
        if obj:
            return obj
        queryset = self.model._default_manager.untranslated()
        try:
            obj = queryset.get(**self.filter_kwargs())
        except model.DoesNotExist:
            return None
        obj.translate(self._language(self.request))
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

