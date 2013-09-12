try:
    # Django 1.3
    from django.conf.urls.defaults import patterns, include, url
except:
    from django.conf.urls import patterns, include, url
from django.contrib import admin
from hvad.test_utils.project.app.views import NormalUpdateView

admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    url(r'update/normal/(?P<object_id>\d+)/', NormalUpdateView.as_view(), name="update_normal"),
    url(r'update/normal/(?P<slug>\w+)/slug/', NormalUpdateView.as_view(), name="update_normal_slug"),
)
