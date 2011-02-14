from django.contrib import admin
from nani.admin import TranslateableAdmin
from models import Normal


admin.site.register(Normal, TranslateableAdmin)