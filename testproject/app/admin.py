from django.contrib import admin
from models import Normal
from nani.admin import TranslateableAdmin
from testproject.app.models import Standard


admin.site.register(Normal, TranslateableAdmin)
admin.site.register(Standard)