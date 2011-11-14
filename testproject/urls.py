from django.conf.urls.defaults import *

from django.contrib import admin
from testproject.app.views import NormalUpdateView

admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    url(r'update/normal/(?P<object_id>\d+)/', NormalUpdateView.as_view(), name="update_normal"),
    url(r'update/normal/(?P<slug>\w+)/slug/', NormalUpdateView.as_view(), name="update_normal_slug"),
)
