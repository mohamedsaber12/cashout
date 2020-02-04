"""payouts URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from two_factor.urls import urlpatterns as tf_urls
from data.views import protected_serve
from .decorators import protected_media_serve

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('admin/', admin.site.urls),
        path('__debug__/', include(debug_toolbar.urls)),
    ]
else:
    urlpatterns = [
        path('secure-portal/', admin.site.urls),
    ]

    handler404 = 'payouts.views.page_not_found_view'

    handler500 = 'payouts.views.error_view'

    handler403 = 'payouts.views.permission_denied_view'

    handler400 = 'payouts.views.bad_request_view'

    handler401 = 'payouts.views.unauthorized_view'


urlpatterns += [    
    path('i18n/', include('django.conf.urls.i18n')),
    path('', include('data.urls', namespace='data')),
    path('', include('users.urls', namespace='users')),
    path('', include('disb.urls', namespace='disbursement')),
    path('', include(tf_urls, namespace='two_factor')),
    path('api/secure/', include('disb.api.urls', namespace='disbursement_api')),
    path('api/secure/', include('data.api.urls', namespace='data_api')),
    path('api/secure/', include('payment.api.urls', namespace='payment_api'))
]

urlpatterns += static(settings.MEDIA_URL + 'documents/',
                      document_root=settings.MEDIA_ROOT, view=protected_serve)

urlpatterns += static(settings.MEDIA_URL,
                      document_root=settings.MEDIA_ROOT, view=protected_media_serve)
