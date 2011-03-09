from django.contrib.admin.options import ModelAdmin
from django.contrib.admin.util import flatten_fieldsets
from django.utils.functional import curry
from django.utils.translation import ugettext_lazy as _
from nani.forms import TranslateableModelForm



def translateable_modelform_factory(model, form=TranslateableModelForm,
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

class TranslateableAdmin(ModelAdmin):
    
    form = TranslateableModelForm
    
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
        defaults = {
            "form": self.form,
            "fields": fields,
            "exclude": exclude,
            "formfield_callback": curry(self.formfield_for_dbfield, 
                                        request=request),
        }
        defaults.update(kwargs)
        return translateable_modelform_factory(self.model, **defaults)
    
    def all_translations(self, obj):
        """
        use this to display all languages the object has been translated to
        in the changelist view:
        
        class MyAdmin(admin.ModelAdmin):
            list_display = ('__str__', 'all_translations',)
        
        """
        if obj and obj.pk:
            languages = []
            for language in [t.language_code for t in obj.translations.all()]:
                if language == obj.language_code:
                    languages.append(u'<strong>%s</strong>' % language)
                else:
                    languages.append(language)
            return u' '.join(languages)
        else:
            return ''
    all_translations.allow_tags = True
    all_translations.short_description = _('all translations')