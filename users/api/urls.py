from django.urls import path

from .views import (OnboardPortalUser)


app_name = 'user_api'

urlpatterns = [
     path('onboard-user/', OnboardPortalUser, name='onboard-user'),
]
