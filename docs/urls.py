from django.urls import re_path, path
from django.views.generic import TemplateView

from .views import serve_docs


app_name = 'docs'


urlpatterns = [
    path('docs/swagger-ui/', TemplateView.as_view(
            template_name='instant_cashin/swagger_api_docs.html',
            extra_context={'schema_url': 'openapi-schema'}
        ), name='swagger-ui'),
    re_path(r'^docs/(?P<path>.*)$', serve_docs, name='instant_docs'),
]
