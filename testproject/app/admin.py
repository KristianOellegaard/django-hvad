from django.contrib import admin
from models import Normal
from nani.admin import TranslateableAdmin


admin.site.register(Normal, TranslateableAdmin)