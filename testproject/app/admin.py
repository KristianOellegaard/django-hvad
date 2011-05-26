from django.contrib import admin
from models import Normal, SimpleRelated
from nani.admin import TranslatableAdmin


admin.site.register(Normal, TranslatableAdmin)
admin.site.register(SimpleRelated, TranslatableAdmin)