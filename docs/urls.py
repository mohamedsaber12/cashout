from django.urls import re_path

from .views import serve_docs


urlpatterns = [
    re_path(r'^docs/(?P<path>.*)$', serve_docs),
]
