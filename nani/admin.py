from django.conf import settings
from django.contrib.admin.options import ModelAdmin
from django.contrib.admin.util import flatten_fieldsets
from django.core.exceptions import ValidationError
from django.template import TemplateDoesNotExist
from django.template.loader import find_template
from django.utils.functional import curry
from django.utils.translation import ugettext_lazy as _, get_language
from nani.forms import TranslatableModelForm
import urllib


def translatable_modelform_factory(model, form=TranslatableModelForm,
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
    return type(class_name, (form,), form_class_attrs)


class TranslatableAdmin(ModelAdmin):
    
    query_language_key = 'language'
    
    form = TranslatableModelForm
    
    change_form_template = 'admin/nani/change_form.html'
    
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
        # if exclude is an empty list we pass None to be consistant with the
        # default on modelform_factory
        exclude = exclude or None
        old_formfield_callback = curry(self.formfield_for_dbfield, 
                                       request=request)
        defaults = {
            "form": self.form,
            "fields": fields,
            "exclude": exclude,
            "formfield_callback": old_formfield_callback,
        }
        defaults.update(kwargs)
        return translatable_modelform_factory(self.model, **defaults)
    
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
        context['title'] = '%s (%s)' % (context['title'], self._language(request))
        context['language_tabs'] = self.get_language_tabs(request, obj)
        context['base_template'] = self.get_change_form_base_template()
        return super(TranslatableAdmin, self).render_change_form(request,
                                                                  context,
                                                                  add, change,
                                                                  form_url, obj)
        
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
    
    def get_language_tabs(self, request, obj):
        tabs = []
        get = dict(request.GET)
        language = self._language(request)
        available_languages = []
        if obj:
            available_languages = obj.get_available_languages()
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
            tabs.append((url, name, status))
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
