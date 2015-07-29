from django.views.generic.detail import SingleObjectMixin, SingleObjectTemplateResponseMixin
from django.views.generic.edit import ModelFormMixin, ProcessFormView, BaseDeleteView
from django.utils.translation import get_language
from hvad.forms import translatable_modelform_factory
from hvad.utils import collect_context_modifiers
import warnings

class _TransitionObjectMixin(SingleObjectMixin):
    # Remove in 1.5
    def get_object(self, queryset=None):
        assert not callable(getattr(self, '_get_object', None)), (
            'Method \'_get_object()\' was removed. Please update view %s to use '
            '\'get_object()\' instead.' % self.__class__.__name__)

        assert not callable(getattr(self, 'filter_kwargs', None)), (
            'Method \'filter_kwargs()\' was removed. Please update view %s to use '
            '\'get_queryset()\' or \'get_object()\'.' % self.__class__.__name__)

        assert not (self.pk_url_kwarg == 'pk' and 'object_id' in self.kwargs and 'pk' not in self.kwargs), (
            'Default view argument for pk has changed from \'object_id\' '
            'to \'pk\'. Please update view %s.' % self.__class__.__name__)

        return super(_TransitionObjectMixin, self).get_object(queryset)


class TranslatableModelFormMixin(ModelFormMixin, _TransitionObjectMixin):
    ''' ModelFormMixin that works with an TranslatableModelForm in **enforce** mode '''
    query_language_key = 'language'

    def get_language(self):
        # Remove in 1.5
        assert not callable(getattr(self, '_language', None)), (
            'Method \'_language\' has been renamed to \'get_language()\'. '
            'Please update view %s.' % self.__class__.__name__)
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
from hvad.admin import TranslatableModelAdminMixin
from hvad.forms import TranslatableModelForm

class TranslatableBaseView(UpdateView, TranslatableModelAdminMixin): #pragma: no cover
    # Remove in 1.5
    form_class = TranslatableModelForm

    def __init__(self, *args, **kwargs):
        raise AssertionError(
            'TranslatableBaseView has been removed. Please update view %s to use '
            'new Django-compliant view instead.' % self.__class__.__name__
        )
