from django.contrib import admin
from hvad.test_utils.project.app.models import Normal, Unique, SimpleRelated, LimitedChoice, AutoPopulated
from hvad.admin import TranslatableAdmin, TranslatableTabularInline

class SimpleRelatedInline(TranslatableTabularInline):
    model = SimpleRelated

class NormalAdmin(TranslatableAdmin):
    inlines = [SimpleRelatedInline,]

admin.site.register(Normal, NormalAdmin)
admin.site.register(Unique, TranslatableAdmin)
admin.site.register(SimpleRelated, TranslatableAdmin)
admin.site.register(LimitedChoice)
admin.site.register(AutoPopulated, TranslatableAdmin)

