import django
from django.contrib import admin
from hvad.test_utils.project.app.models import (Normal, SimpleRelated, AdvancedAdminModel,
                                                LimitedChoice, AutoPopulated)
from hvad.admin import TranslatableAdmin, TranslatableTabularInline

class SimpleRelatedInline(TranslatableTabularInline):
    model = SimpleRelated

class NormalAdmin(TranslatableAdmin):
    inlines = [SimpleRelatedInline,]

if django.VERSION >= (1, 7):
    class AdvancedAdmin(TranslatableAdmin):
        # Options for list pages
        list_display = (
            'shared', 'time_field',
            'translated', 'translated_ro', 'translated_hidden',
        )
        list_display_links = (
            'time_field', 'translated',
        )
        list_editable = ('shared',) # translated fields are not supported here
        list_select_related = ('translated_rel',)
        raw_id_fields = ('translated_rel',)

        # list_filter - must not work on translated fields
        # ordering - not handled on translated fields
        # search_fields - not handled on translated fields


        # Options for editing pages
        fields = ('shared', 'translated', 'translated_ro')
        exclude = ('translated_hidden',)
        readonly_fields = ('translated_ro',)
        prepopulated_fields = {
            'translated': ('shared',),
        }
    admin.site.register(AdvancedAdminModel, AdvancedAdmin)


admin.site.register(Normal, NormalAdmin)
admin.site.register(SimpleRelated, TranslatableAdmin)
admin.site.register(LimitedChoice)
admin.site.register(AutoPopulated, TranslatableAdmin)

