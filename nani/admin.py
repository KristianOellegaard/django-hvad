from distutils.version import LooseVersion
from django.conf import settings
from django.contrib.admin.options import ModelAdmin, csrf_protect_m, InlineModelAdmin
from django.contrib.admin.util import (flatten_fieldsets, unquote, 
    get_deleted_objects)
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.urlresolvers import reverse
from django.db import router, transaction
from django.forms.formsets import formset_factory
from django.forms.models import ModelForm, BaseModelFormSet, BaseInlineFormSet, model_to_dict
from django.forms.util import ErrorList
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import TemplateDoesNotExist
from django.template.context import RequestContext
from django.template.loader import find_template
from django.utils.encoding import iri_to_uri, force_unicode
from django.utils.functional import curry
from django.utils.translation import ugettext_lazy as _, get_language
from functools import update_wrapper
from nani.forms import TranslatableModelForm, translatable_inlineformset_factory, translatable_modelform_factory
import django
import urllib
from nani.utils import get_cached_translation, get_translation
from nani.manager import FALLBACK_LANGUAGES


NEW_GET_DELETE_OBJECTS = LooseVersion(django.get_version()) >= LooseVersion('1.3')


def get_language_name(language_code):
    return dict(settings.LANGUAGES).get(language_code, language_code)

class InlineModelForm(TranslatableModelForm):
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=':',
                 empty_permitted=False, instance=None):
        """

        """
        opts = self._meta
        model_opts = opts.model._meta
        object_data = {}
        language = getattr(self, 'language', get_language())
        if instance is not None:
            trans = get_cached_translation(instance)
            if not trans or trans.language_code != language:
                try:
                    trans = get_translation(instance, language)
                except model_opts.translations_model.DoesNotExist:
                    trans = None
            if trans:
                object_data = model_to_dict(trans, opts.fields, opts.exclude)
                # Dirty hack that swaps the id from the translation id, to the master id
                # This is necessary, because we in this case get the untranslated instance,
                # and thereafter get the correct translation on save.
                if object_data.has_key("id"):
                    object_data["id"] = trans.master.id
        if initial is not None:
            object_data.update(initial)
        initial = object_data
        super(TranslatableModelForm, self).__init__(data, files, auto_id,
                                                     prefix, initial,
                                                     error_class, label_suffix,
                                                     empty_permitted, instance)


class TranslatableModelAdminMixin(object):
    query_language_key = 'language'

    def all_translations(self, obj):
        """
        use this to display all languages the object has been translated to
        in the changelist view:

        class MyAdmin(admin.ModelAdmin):
            list_display = ('__str__', 'all_translations',)

        """
        if obj and obj.pk:
            languages = []
            current_language = get_language()
            for language in obj.get_available_languages():
                if language == current_language:
                    languages.append(u'<strong>%s</strong>' % language)
                else:
                    languages.append(language)
            return u' '.join(languages)
        else:
            return ''
    all_translations.allow_tags = True
    all_translations.short_description = _('all translations')

    def get_available_languages(self, obj):
        if obj:
            return obj.get_available_languages()
        else:
            return []

    def get_language_tabs(self, request, available_languages):
        tabs = []
        get = dict(request.GET)
        language = self._language(request)
        for key, name in settings.LANGUAGES:
            get.update({'language': key})
            url = '%s://%s%s?%s' % (request.is_secure() and 'https' or 'http',
                                    request.get_host(), request.path,
                                    urllib.urlencode(get))
            if language == key:
                status = 'current'
            elif key in available_languages:
                status = 'available'
            else:
                status = 'empty'
            tabs.append((url, name, key, status))
        return tabs

    def _language(self, request):
        return request.GET.get(self.query_language_key, get_language())


class TranslatableAdmin(ModelAdmin, TranslatableModelAdminMixin):
    form = TranslatableModelForm
    
    change_form_template = 'admin/nani/change_form.html'
    
    deletion_not_allowed_template = 'admin/nani/deletion_not_allowed.html'
    
    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        
        urlpatterns = super(TranslatableAdmin, self).get_urls()

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.module_name

        urlpatterns = patterns('',
            url(r'^(.+)/delete-translation/(.+)/$',
                wrap(self.delete_translation),
                name='%s_%s_delete_translation' % info),
        ) + urlpatterns
        return urlpatterns
    
    def get_form(self, request, obj=None, **kwargs):
        """
        Returns a Form class for use in the admin add view. This is used by
        add_view and change_view.
        """
        
        if self.declared_fieldsets:
            fields = flatten_fieldsets(self.declared_fieldsets)
        else:
            fields = None
        if self.exclude is None:
            exclude = []
        else:
            exclude = list(self.exclude)
        exclude.extend(kwargs.get("exclude", []))
        exclude.extend(self.get_readonly_fields(request, obj))
        # Exclude language_code, adding it again to the instance is done by
        # the LanguageAwareCleanMixin (see translatable_modelform_factory)
        exclude.append('language_code')
        old_formfield_callback = curry(self.formfield_for_dbfield, 
                                       request=request)
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
        lang = get_language_name(lang_code)
        available_languages = self.get_available_languages(obj)
        context['title'] = '%s (%s)' % (context['title'], lang)
        context['current_is_translated'] = lang_code in available_languages
        context['allow_deletion'] = len(available_languages) > 1
        context['language_tabs'] = self.get_language_tabs(request, available_languages)
        context['base_template'] = self.get_change_form_base_template()
        return super(TranslatableAdmin, self).render_change_form(request,
                                                                  context,
                                                                  add, change,
                                                                  form_url, obj)
        
    def response_change(self, request, obj):
        redirect = super(TranslatableAdmin, self).response_change(request, obj)
        uri = iri_to_uri(request.path)
        if redirect['Location'] in (uri, "../add/"):
            if self.query_language_key in request.GET:
                redirect['Location'] = '%s?%s=%s' % (redirect['Location'],
                    self.query_language_key, request.GET[self.query_language_key])
        return redirect
    
    @csrf_protect_m
    @transaction.commit_on_success
    def delete_translation(self, request, object_id, language_code):
        "The 'delete translation' admin view for this model."
        opts = self.model._meta
        app_label = opts.app_label
        translations_model = opts.translations_model
        
        try:
            obj = translations_model.objects.select_related('maser').get(
                                                master__pk=unquote(object_id),
                                                language_code=language_code)
        except translations_model.DoesNotExist:
            raise Http404

        if not self.has_delete_permission(request, obj):
            raise PermissionDenied
        
        if len(self.get_available_languages(obj.master)) <= 1:
            return self.deletion_not_allowed(request, obj, language_code)

        using = router.db_for_write(translations_model)

        # Populate deleted_objects, a data structure of all related objects that
        # will also be deleted.
        
        protected = False
        if NEW_GET_DELETE_OBJECTS:
            (deleted_objects, perms_needed, protected) = get_deleted_objects(
                [obj], translations_model._meta, request.user, self.admin_site, using)
        else: # pragma: no cover
            (deleted_objects, perms_needed) = get_deleted_objects(
                [obj], translations_model._meta, request.user, self.admin_site)
        
        
        lang = get_language_name(language_code) 
            

        if request.POST: # The user has already confirmed the deletion.
            if perms_needed:
                raise PermissionDenied
            obj_display = '%s translation of %s' % (lang, force_unicode(obj.master))
            self.log_deletion(request, obj, obj_display)
            self.delete_model_translation(request, obj)

            self.message_user(request,
                _('The %(name)s "%(obj)s" was deleted successfully.') % {
                    'name': force_unicode(opts.verbose_name),
                    'obj': force_unicode(obj_display)
                }
            )

            if not self.has_change_permission(request, None):
                return HttpResponseRedirect(reverse('admin:index'))
            return HttpResponseRedirect(reverse('admin:%s_%s_changelist' % (opts.app_label, opts.module_name)))

        object_name = '%s Translation' % force_unicode(opts.verbose_name)

        if perms_needed or protected:
            title = _("Cannot delete %(name)s") % {"name": object_name}
        else:
            title = _("Are you sure?")

        context = {
            "title": title,
            "object_name": object_name,
            "object": obj,
            "deleted_objects": deleted_objects,
            "perms_lacking": perms_needed,
            "protected": protected,
            "opts": opts,
            "root_path": self.admin_site.root_path,
            "app_label": app_label,
        }

        return render_to_response(self.delete_confirmation_template or [
            "admin/%s/%s/delete_confirmation.html" % (app_label, opts.object_name.lower()),
            "admin/%s/delete_confirmation.html" % app_label,
            "admin/delete_confirmation.html"
        ], context, RequestContext(request))
    
    def deletion_not_allowed(self, request, obj, language_code):
        opts = self.model._meta
        app_label = opts.app_label
        object_name = force_unicode(opts.verbose_name)
        
        context = RequestContext(request)
        context['object'] = obj.master
        context['language_code'] = language_code
        context['opts'] = opts
        context['app_label'] = app_label
        context['language_name'] = get_language_name(language_code)
        context['object_name'] = object_name
        return render_to_response(self.deletion_not_allowed_template, context)
        
    def delete_model_translation(self, request, obj):
        obj.delete()
    
    def get_object(self, request, object_id):
        obj = super(TranslatableAdmin, self).get_object(request, object_id)
        if obj:
            return obj
        queryset = self.model.objects.untranslated()
        model = self.model
        try:
            object_id = model._meta.pk.to_python(object_id)
            obj = queryset.get(pk=object_id)
        except (model.DoesNotExist, ValidationError):
            return None
        new_translation = model._meta.translations_model()
        new_translation.language_code = self._language(request)
        new_translation.master = obj
        setattr(obj, model._meta.translations_cache, new_translation)
        return obj

    def queryset(self, request):
        language = self._language(request)
        languages = [language,]
        for lang in FALLBACK_LANGUAGES:
            if not lang in languages:
                languages.append(lang)
        qs = self.model._default_manager.untranslated().use_fallbacks(*languages)
        # TODO: this should be handled by some parameter to the ChangeList.
        ordering = self.ordering or () # otherwise we might try to *None, which is bad ;)
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
        for template in search_templates:
            try:
                find_template(template)
                return template
            except TemplateDoesNotExist:
                pass
        else: # pragma: no cover
            pass

class TranslatableInlineModelAdmin(InlineModelAdmin, TranslatableModelAdminMixin):
    form = InlineModelForm

    change_form_template = 'admin/nani/change_form.html'

    deletion_not_allowed_template = 'admin/nani/deletion_not_allowed.html'

    def get_formset(self, request, obj=None, **kwargs):
        """Returns a BaseInlineFormSet class for use in admin add/change views."""
        if self.declared_fieldsets:
            fields = flatten_fieldsets(self.declared_fieldsets)
        else:
            fields = None
        if self.exclude is None:
            exclude = []
        else:
            exclude = list(self.exclude)
        exclude.extend(kwargs.get("exclude", []))
        exclude.extend(self.get_readonly_fields(request, obj))
        # if exclude is an empty list we use None, since that's the actual
        # default
        exclude = exclude or None
        defaults = {
            "form": self.get_form(request, obj),
            #"formset": self.formset,
            "fk_name": self.fk_name,
            "fields": fields,
            "exclude": exclude,
            "formfield_callback": curry(self.formfield_for_dbfield, request=request),
            "extra": self.extra,
            "max_num": self.max_num,
            "can_delete": self.can_delete,
        }
        defaults.update(kwargs)
        language = self._language(request)
        return translatable_inlineformset_factory(language, self.parent_model, self.model, **defaults)

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url

        urlpatterns = super(InlineModelAdmin, self).get_urls()

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.module_name

        urlpatterns = patterns('',
            url(r'^(.+)/delete-translation/(.+)/$',
                wrap(self.delete_translation),
                name='%s_%s_delete_translation' % info),
        ) + urlpatterns
        return urlpatterns

    def get_form(self, request, obj=None, **kwargs):
        """
        Returns a Form class for use in the admin add view. This is used by
        add_view and change_view.
        """
        if self.declared_fieldsets:
            fields = flatten_fieldsets(self.declared_fieldsets)
        else:
            fields = None
        if self.exclude is None:
            exclude = []
        else:
            exclude = list(self.exclude)
        exclude.extend(kwargs.get("exclude", []))
        exclude.extend(self.get_readonly_fields(request, obj))
        # Exclude language_code, adding it again to the instance is done by
        # the LanguageAwareCleanMixin (see translatable_modelform_factory)
        exclude.append('language_code')
        old_formfield_callback = curry(self.formfield_for_dbfield,
                                       request=request)
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

    """
# Should be added
    @csrf_protect_m
    @transaction.commit_on_success
    def delete_translation(self, request, object_id, language_code):
        "The 'delete translation' admin view for this model."
        opts = self.model._meta
        app_label = opts.app_label
        translations_model = opts.translations_model

        try:
            obj = translations_model.objects.select_related('maser').get(
                                                master__pk=unquote(object_id),
                                                language_code=language_code)
        except translations_model.DoesNotExist:
            raise Http404

        if not self.has_delete_permission(request, obj):
            raise PermissionDenied

        if len(self.get_available_languages(obj.master)) <= 1:
            return self.deletion_not_allowed(request, obj, language_code)

        using = router.db_for_write(translations_model)

        # Populate deleted_objects, a data structure of all related objects that
        # will also be deleted.

        protected = False
        if NEW_GET_DELETE_OBJECTS:
            (deleted_objects, perms_needed, protected) = get_deleted_objects(
                [obj], translations_model._meta, request.user, self.admin_site, using)
        else: # pragma: no cover
            (deleted_objects, perms_needed) = get_deleted_objects(
                [obj], translations_model._meta, request.user, self.admin_site)


        lang = get_language_name(language_code)


        if request.POST: # The user has already confirmed the deletion.
            if perms_needed:
                raise PermissionDenied
            obj_display = '%s translation of %s' % (lang, force_unicode(obj.master))
            self.log_deletion(request, obj, obj_display)
            self.delete_model_translation(request, obj)

            self.message_user(request,
                _('The %(name)s "%(obj)s" was deleted successfully.') % {
                    'name': force_unicode(opts.verbose_name),
                    'obj': force_unicode(obj_display)
                }
            )

            if not self.has_change_permission(request, None):
                return HttpResponseRedirect(reverse('admin:index'))
            return HttpResponseRedirect(reverse('admin:%s_%s_changelist' % (opts.app_label, opts.module_name)))

        object_name = '%s Translation' % force_unicode(opts.verbose_name)

        if perms_needed or protected:
            title = _("Cannot delete %(name)s") % {"name": object_name}
        else:
            title = _("Are you sure?")

        context = {
            "title": title,
            "object_name": object_name,
            "object": obj,
            "deleted_objects": deleted_objects,
            "perms_lacking": perms_needed,
            "protected": protected,
            "opts": opts,
            "root_path": self.admin_site.root_path,
            "app_label": app_label,
        }

        return render_to_response(self.delete_confirmation_template or [
            "admin/%s/%s/delete_confirmation.html" % (app_label, opts.object_name.lower()),
            "admin/%s/delete_confirmation.html" % app_label,
            "admin/delete_confirmation.html"
        ], context, RequestContext(request))

    def deletion_not_allowed(self, request, obj, language_code):
        opts = self.model._meta
        app_label = opts.app_label
        object_name = force_unicode(opts.verbose_name)

        context = RequestContext(request)
        context['object'] = obj.master
        context['language_code'] = language_code
        context['opts'] = opts
        context['app_label'] = app_label
        context['language_name'] = get_language_name(language_code)
        context['object_name'] = object_name
        return render_to_response(self.deletion_not_allowed_template, context)

    def delete_model_translation(self, request, obj):
        obj.delete()
    """
    def queryset(self, request):
        language = self._language(request)
        qs = self.model._default_manager.all()#.language(language)
        # TODO: this should be handled by some parameter to the ChangeList.
        ordering = self.ordering or () # otherwise we might try to *None, which is bad ;)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs


class TranslatableStackedInline(TranslatableInlineModelAdmin):
    template = 'admin/nani/edit_inline/stacked.html'

class TranslatableTabularInline(TranslatableInlineModelAdmin):
    template = 'admin/nani/edit_inline/tabular.html'