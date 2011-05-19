from distutils.version import LooseVersion
from django.conf import settings
from django.contrib.admin.options import ModelAdmin, csrf_protect_m
from django.contrib.admin.util import (flatten_fieldsets, unquote, 
    get_deleted_objects)
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.urlresolvers import reverse
from django.db import router, transaction
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import TemplateDoesNotExist
from django.template.context import RequestContext
from django.template.loader import find_template
from django.utils.encoding import iri_to_uri, force_unicode
from django.utils.functional import curry
from django.utils.translation import ugettext_lazy as _, get_language
from functools import update_wrapper
from nani.forms import TranslatableModelForm
import django
import urllib


NEW_GET_DELETE_OBJECTS = LooseVersion(django.get_version()) >= LooseVersion('1.3')


def get_language_name(language_code):
    return dict(settings.LANGUAGES).get(language_code, language_code)

class CleanMixin(object):
    def clean(self):
        data = super(CleanMixin, self).clean()
        data['language_code'] = self.language
        return data


def LanguageAwareCleanMixin(language):
    return type('BoundCleanMixin', (CleanMixin,), {'language': language})


def translatable_modelform_factory(language, model, form=TranslatableModelForm,
                                   fields=None, exclude=None,
                                   formfield_callback=None):
    # Create the inner Meta class. FIXME: ideally, we should be able to
    # construct a ModelForm without creating and passing in a temporary
    # inner class.

    # Build up a list of attributes that the Meta object will have.
    attrs = {'model': model}
    if fields is not None:
        attrs['fields'] = fields
    if exclude is not None:
        attrs['exclude'] = exclude

    # If parent form class already has an inner Meta, the Meta we're
    # creating needs to inherit from the parent's inner meta.
    parent = (object,)
    if hasattr(form, 'Meta'):
        parent = (form.Meta, object)
    Meta = type('Meta', parent, attrs)

    # Give this new form class a reasonable name.
    class_name = model.__name__ + 'Form'

    # Class attributes for the new form class.
    form_class_attrs = {
        'Meta': Meta,
        'formfield_callback': formfield_callback
    }
    clean_mixin = LanguageAwareCleanMixin(language)
    return type(class_name, (clean_mixin, form,), form_class_attrs)


class TranslatableAdmin(ModelAdmin):
    
    query_language_key = 'language'
    
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

    def get_available_languages(self, obj):
        if obj:
            return obj.get_available_languages()
        else:
            return []
    
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
        qs = super(TranslatableAdmin, self).queryset(request)
        return qs.language(language)
    
    def _language(self, request):
        return request.GET.get(self.query_language_key, get_language())
    
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
