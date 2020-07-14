# -*- coding: utf-8 -*-

from django.urls import path

from .views import GeneratePDFView


app_name = 'utilities'

urlpatterns = [
    path('generate-report/', GeneratePDFView.as_view(), name='generate_report'),
]
