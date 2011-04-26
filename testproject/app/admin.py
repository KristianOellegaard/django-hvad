from django.contrib import admin
from models import Normal
from nani.admin import TranslatableAdmin


admin.site.register(Normal, TranslatableAdmin)
