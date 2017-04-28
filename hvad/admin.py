import functools
import warnings
import django
from django.contrib.admin.options import ModelAdmin, csrf_protect_m, InlineModelAdmin
from django.contrib.admin.utils import flatten_fieldsets, unquote, get_deleted_objects
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist, PermissionDenied, ValidationError
if django.VERSION >= (1, 10):
    from django.urls import reverse
else:
    from django.core.urlresolvers import reverse
from django.db import router, transaction
from django.forms.models import model_to_dict
from django.forms.utils import ErrorList
from django.http import Http404, HttpResponseRedirect, QueryDict
from django.shortcuts import render
from django.template import TemplateDoesNotExist
from django.template.loader import select_template
from django.utils.encoding import iri_to_uri, force_text
from django.utils.functional import curry
from django.utils.translation import ugettext_lazy as _, get_language, get_language_info
from hvad.compat import urlencode, urlparse
from hvad.forms import TranslatableModelForm, translatable_inlineformset_factory, translatable_modelform_factory
from hvad.settings import hvad_settings
from hvad.utils import load_translation
from hvad.manager import TranslationQueryset

__all__ = (
    'TranslatableAdmin',
    'TranslatableInlineModelAdmin',
    'TranslatableStackedInline',
    'TranslatableTabularInline',
    'InlineModelForm',
)


class InlineModelForm(TranslatableModelForm):
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=':',
                 empty_permitted=False, instance=None, **kwargs):
        """

        """
        opts = self._meta
        object_data = {}
        language = getattr(self, 'language', get_language())
        if instance is not None:
            trans = load_translation(instance, language, enforce=True)
            if trans.pk:
                object_data = model_to_dict(trans, opts.fields, opts.exclude)
                # Dirty hack that swaps the id from the translation id, to the master id
                # This is necessary, because we in this case get the untranslated instance,
                # and thereafter get the correct translation on save.
                if "id" in object_data:
                    object_data["id"] = trans.master.id
        object_data.update(initial or {})
        super(TranslatableModelForm, self).__init__(data, files, auto_id,
                                                     prefix, object_data,
                                                     error_class, label_suffix,
                                                     empty_permitted, instance, **kwargs)


class TranslatableModelAdminMixin(object):
    query_language_key = 'language'

    def all_translations(self, obj):
        """ Get an HTML-formatted list of all translations, with links to admin pages """
        if obj is None or not obj.pk:
            return ''

        languages = []
        current_language = get_language()
        for language in obj.get_available_languages():
            entry = u'<a href="%s">%s</a>' % (self.get_url(obj, lang=language), language)
            if language == current_language:
                entry = u'<strong>%s</strong>' % entry
            languages.append(entry)
        return u', '.join(languages)
    all_translations.allow_tags = True
    all_translations.short_description = _(u'all translations')

    def get_available_languages(self, obj):
        # remove in 1.9
        raise NotImplementedError(
            'admin.get_available_languages is obsolete and has been removed. '
            'Invoke the instance\'s get_available_languages() method directly.'
        )

    def get_language_tabs(self, obj, request, available_languages):
        info = None if obj is None else (obj._meta.app_label, obj._meta.model_name)
        tabs = []
        get = request.GET.copy()
        language = self._language(request)
        for key, name in hvad_settings.LANGUAGES:
            get['language'] = key
            url = '%s?%s' % (request.path, get.urlencode())
            if language == key:
                status = 'current'
            elif key in available_languages:
                status = 'available'
            else:
                status = 'empty'
            del_url = (reverse('admin:%s_%s_delete_translation' % info, args=(obj.pk, key))
                       if obj is not None and key in available_languages else None)
            tabs.append((url, name, key, status, del_url))
        return tabs

    def _language(self, request):
        return request.GET.get(self.query_language_key, get_language())


class TranslatableAdmin(ModelAdmin, TranslatableModelAdminMixin):
    form = TranslatableModelForm
    
    change_form_template = 'admin/hvad/change_form.html'
    
    deletion_not_allowed_template = 'admin/hvad/deletion_not_allowed.html'
    
    def __init__(self, *args, **kwargs):
        super(TranslatableAdmin, self).__init__(*args, **kwargs)
        self.reverse = functools.partial(reverse, current_app=self.admin_site.name)


    def get_url(self, obj, lang=None, get={}):
        ct = ContentType.objects.get_for_model(self.model)
        info = ct.app_label, ct.model
        if lang:
            get.update({self.query_language_key: lang})
        url = '%s?%s' % (self.reverse('admin:%s_%s_change' % info, args=(obj.pk,)), urlencode(get))
        return url


    def get_urls(self):
        from django.conf.urls import url
        urlpatterns = super(TranslatableAdmin, self).get_urls()
        info = self.model._meta.app_label, self.model._meta.model_name
        return [
            url(r'^(.+)/delete-translation/(.+)/$',
                self.admin_site.admin_view(self.delete_translation),
                name='%s_%s_delete_translation' % info),
        ] + urlpatterns
    
    def get_form(self, request, obj=None, **kwargs):
        """
        Returns a Form class for use in the admin add view. This is used by
        add_view and change_view.
        """
        if 'fields' in kwargs:
            fields = kwargs.pop('fields')
        else:
            fields = flatten_fieldsets(self.get_fieldsets(request, obj))
        exclude = (
            tuple(self.exclude or ()) +
            tuple(kwargs.pop("exclude", ())) +
            tuple(self.get_readonly_fields(request, obj) or ())
        )
        old_formfield_callback = curry(self.formfield_for_dbfield, request=request)
        defaults = {
            "form": self.form,
            "fields": fields,
            "exclude": exclude,
            "formfield_callback": old_formfield_callback,
        }
        defaults.update(kwargs)
        language = self._language(request)
        return translatable_modelform_factory(language, self.model, **defaults)
    

    
    def render_change_form(self, request, context, add=False, change=False,
                           form_url='', obj=None):
        lang_code = self._language(request)
        lang = get_language_info(lang_code)['name_local']
        available_languages = [] if obj is None else obj.get_available_languages()

        context.update({
            'title': '%s (%s)' % (context['title'], lang),
            'current_is_translated': lang_code in available_languages,
            'allow_deletion': len(available_languages) > 1,
            'language_tabs': self.get_language_tabs(obj, request, available_languages),
            'base_template': self.get_change_form_base_template(),
        })

        # Ensure form action url carries over tab language
        qs_language = request.GET.get('language')
        if qs_language:
            form_url = urlparse(form_url or request.get_full_path())
            query = QueryDict(form_url.query, mutable=True)
            if 'language' not in query:
                query['language'] = qs_language
            form_url = form_url._replace(query=query.urlencode()).geturl()

        return super(TranslatableAdmin, self).render_change_form(request,
                                                                  context,
                                                                  add, change,
                                                                  form_url, obj)
        
    def response_change(self, request, obj):
        response = super(TranslatableAdmin, self).response_change(request, obj)
        if 'Location' in response:
            uri = iri_to_uri(request.path)
            app_label, model_name = self.model._meta.app_label, self.model._meta.model_name
            if response['Location'] in (uri, "../add/", self.reverse('admin:%s_%s_add' % (app_label, model_name))):
                if self.query_language_key in request.GET:
                    response['Location'] = '%s?%s=%s' % (response['Location'],
                        self.query_language_key, request.GET[self.query_language_key])
        return response
    
    @csrf_protect_m
    @transaction.atomic
    def delete_translation(self, request, object_id, language_code):
        "The 'delete translation' admin view for this model."
        opts = self.model._meta
        app_label = opts.app_label
        translations_model = opts.translations_model
        
        try:
            obj = translations_model.objects.select_related('master').get(
                                                master__pk=unquote(object_id),
                                                language_code=language_code)
        except translations_model.DoesNotExist:
            raise Http404

        if not self.has_delete_permission(request, obj):
            raise PermissionDenied
        
        if len(obj.master.get_available_languages()) <= 1:
            return self.deletion_not_allowed(request, obj, language_code)

        using = router.db_for_write(translations_model)

        # Populate deleted_objects, a data structure of all related objects that
        # will also be deleted.
        
        protected = False
        deleted_objects, model_count, perms_needed, protected = get_deleted_objects(
            [obj], translations_model._meta, request.user, self.admin_site, using)
        
        lang = get_language_info(language_code)['name_local']

        if request.POST: # The user has already confirmed the deletion.
            if perms_needed:
                raise PermissionDenied
            obj_display = u'%s translation of %s' % (force_text(lang), force_text(obj.master))
            self.log_deletion(request, obj, obj_display)
            self.delete_model_translation(request, obj)

            self.message_user(request,
                _(u'The %(name)s "%(obj)s" was deleted successfully.') % {
                    'name': force_text(opts.verbose_name),
                    'obj': force_text(obj_display)
                }
            )

            if not self.has_change_permission(request, None):
                return HttpResponseRedirect(self.reverse('admin:index'))
            return HttpResponseRedirect(self.reverse('admin:%s_%s_changelist' % (opts.app_label, opts.model_name)))

        object_name = _(u'%s Translation') % force_text(opts.verbose_name)

        if perms_needed or protected:
            title = _(u"Cannot delete %(name)s") % {"name": object_name}
        else:
            title = _(u"Are you sure?")

        return render(
            request,
            self.delete_confirmation_template or (
                "admin/%s/%s/delete_confirmation.html" % (app_label, opts.object_name.lower()),
                "admin/%s/delete_confirmation.html" % app_label,
                "admin/delete_confirmation.html"
            ), {
                "title": title,
                "object_name": object_name,
                "object": obj,
                "deleted_objects": deleted_objects,
                "perms_lacking": perms_needed,
                "protected": protected,
                "opts": opts,
                "app_label": app_label,
            },
        )
    
    def deletion_not_allowed(self, request, obj, language_code):
        opts = self.model._meta
        return render(
            request,
            self.deletion_not_allowed_template,
            {
                'object': obj.master,
                'language_code': language_code,
                'opts': opts,
                'app_label': opts.app_label,
                'language_name': get_language_info(language_code)['name_local'],
                'object_name': force_text(opts.verbose_name),
            },
        )
        
    def delete_model_translation(self, request, obj):
        obj.delete()
    
    def get_object(self, request, object_id, from_field=None):
        queryset = self.get_queryset(request)
        if isinstance(queryset, TranslationQueryset): # will always be true once Django 1.9 is required
            model = queryset.shared_model
            if from_field is None:
                field = model._meta.pk
            else:
                try:
                    field = model._meta.get_field(from_field)
                except FieldDoesNotExist:
                    field = model._meta.translations_model._meta.get_field(from_field)
        else:
            model = queryset.model
            field = model._meta.pk if from_field is None else model._meta.get_field(from_field)
        try:
            object_id = field.to_python(object_id)
            obj = queryset.get(**{field.name: object_id})
        except (model.DoesNotExist, ValidationError, ValueError):
            return None

        # object was in queryset - need to make sure we got the right translation
        # we use getattr to trigger a load if instance exists but translation was
        # not cached yet. Should not happen with current code, but is correct,
        # future-proof behavior.
        language_code = getattr(obj, 'language_code', None)
        request_lang = self._language(request)
        if language_code is None or language_code != request_lang:
            # if language does not match that of request, we know request_lang
            # does not exist, because it was the first language in the use_fallbacks
            # list. We prepare it as a new translation.
            obj.translate(request_lang)
        return obj

    def get_queryset(self, request):
        language = self._language(request)
        qs = self.model._default_manager.language(language).fallbacks(*hvad_settings.FALLBACK_LANGUAGES)

        # TODO: this should be handled by some parameter to the ChangeList.
        ordering = getattr(self, 'ordering', None) or ()
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    def get_change_form_base_template(self):
        opts = self.model._meta
        app_label = opts.app_label
        search_templates = [
            "admin/%s/%s/change_form.html" % (app_label, opts.object_name.lower()),
            "admin/%s/change_form.html" % app_label,
            "admin/change_form.html"
        ]
        try:
            return select_template(search_templates)
        except TemplateDoesNotExist: #pragma: no cover
            return None


class TranslatableInlineModelAdmin(InlineModelAdmin, TranslatableModelAdminMixin):
    form = InlineModelForm

    change_form_template = 'admin/hvad/change_form.html'

    deletion_not_allowed_template = 'admin/hvad/deletion_not_allowed.html'

    def get_formset(self, request, obj=None, **kwargs):
        """Returns a BaseInlineFormSet class for use in admin add/change views."""
        if 'fields' in kwargs:
            fields = kwargs.pop('fields')
        else:
            fields = flatten_fieldsets(self.get_fieldsets(request, obj))
        exclude = (
            tuple(self.exclude or ()) +
            tuple(kwargs.pop("exclude", ())) +
            self.get_readonly_fields(request, obj)
        )

        defaults = {
            "form": self.get_form(request, obj, fields=fields),
            "formset": self.formset,
            "fk_name": self.fk_name,
            "fields": fields,
            "exclude": exclude or None,
            "formfield_callback": curry(self.formfield_for_dbfield, request=request),
            "extra": self.extra,
            "max_num": self.max_num,
            "can_delete": self.can_delete,
        }
        defaults.update(kwargs)
        language = self._language(request)
        return translatable_inlineformset_factory(language, self.parent_model, self.model, **defaults)

    def get_urls(self):
        from django.conf.urls import url
        urlpatterns = super(InlineModelAdmin, self).get_urls()

        info = self.model._meta.app_label, self.model._meta.model_name

        return [
            url(r'^(.+)/delete-translation/(.+)/$',
                self.admin_site.admin_view(self.delete_translation),
                name='%s_%s_delete_translation' % info),
        ] + urlpatterns

    def get_form(self, request, obj=None, **kwargs):
        """
        Returns a Form class for use in the admin add view. This is used by
        add_view and change_view.
        """
        if 'fields' in kwargs:
            fields = kwargs.pop('fields')
        else:
            fields = flatten_fieldsets(self.get_fieldsets(request, obj))
        exclude = (
            tuple(self.exclude or ()) +
            tuple(kwargs.pop("exclude", ())) +
            self.get_readonly_fields(request, obj)
        )
        old_formfield_callback = curry(self.formfield_for_dbfield, request=request)
        defaults = {
            "form": self.form,
            "fields": fields,
            "exclude": exclude,
            "formfield_callback": old_formfield_callback,
        }
        defaults.update(kwargs)
        language = self._language(request)
        return translatable_modelform_factory(language, self.model, **defaults)

    def response_change(self, request, obj):
        redirect = super(TranslatableAdmin, self).response_change(request, obj)
        uri = iri_to_uri(request.path)
        if redirect['Location'] in (uri, "../add/"):
            if self.query_language_key in request.GET:
                redirect['Location'] = '%s?%s=%s' % (redirect['Location'],
                    self.query_language_key, request.GET[self.query_language_key])
        return redirect

    def get_queryset(self, request):
        qs = self.model._default_manager.all()#.language(language)
        # TODO: this should be handled by some parameter to the ChangeList.
        ordering = getattr(self, 'ordering', None) or () # otherwise we might try to *None, which is bad ;)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

class TranslatableStackedInline(TranslatableInlineModelAdmin):
    template = 'admin/hvad/edit_inline/stacked.html'

class TranslatableTabularInline(TranslatableInlineModelAdmin):
    template = 'admin/hvad/edit_inline/tabular.html'
