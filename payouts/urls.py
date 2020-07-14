# -*- coding: utf-8 -*-
from __future__ import unicode_literals

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
        path('admin/doc/', include('django.contrib.admindocs.urls')),
        path('admin/', admin.site.urls),
        path('__debug__/', include(debug_toolbar.urls)),
    ]
else:
    urlpatterns = [
        path('secure-portal/doc/', include('django.contrib.admindocs.urls')),
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
    path('', include('disbursement.urls', namespace='disbursement')),
    path('', include('docs.urls', namespace='docs')),
    path('instant-cashin/', include('instant_cashin.urls', namespace='instant_cashin')),
    path('', include(tf_urls, namespace='two_factor')),
    path('utilities/', include('utilities.urls', namespace='utilities')),
    path('api/secure/', include('disbursement.api.urls', namespace='disbursement_api')),
    path('api/secure/', include('data.api.urls', namespace='data_api')),
    path('api/secure/', include('payment.api.urls', namespace='payment_api')),
    path('api/secure/', include('instant_cashin.api.urls', namespace='instant_api')),
]

urlpatterns += static(settings.MEDIA_URL + 'documents/', document_root=settings.MEDIA_ROOT, view=protected_serve)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT, view=protected_media_serve)

# Admin site settings
admin.site.site_header = settings.ADMIN_SITE_HEADER
admin.site.site_title = settings.ADMIN_SITE_TITLE
admin.site.index_title = settings.ADMIN_INDEX_TITLE
