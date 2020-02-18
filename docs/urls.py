from django.urls import re_path

from .views import serve_docs


app_name = 'docs'


urlpatterns = [
    re_path(r'^docs/(?P<path>.*)$', serve_docs, name='instant_docs'),
]
