from django.contrib.auth.views import (PasswordResetCompleteView,
                                       PasswordResetConfirmView,
                                       PasswordResetDoneView,
                                       PasswordResetView,
                                       PasswordChangeView,
                                       PasswordChangeDoneView)
from django.urls import path

from users import views

app_name = 'users'

urlpatterns = [
    path('user/login/', views.login_view,
         name='user_login_view'),
    path('user/logout/', views.ourlogout, name='logout'),
    path('change_password/<user>/', views.change_password, name="change_password"),
    path('password/reset/done/', PasswordResetDoneView.as_view(),
         name='password_reset_done'),
    path('password/reset/', PasswordResetView.as_view(),
         {'post_reset_redirect': '/password/reset/done/',
          'html_email_template_name': 'registration/password_reset_email.html'},
         name='password_reset_done'),
    path('password/reset/<uidb64>/<token>/',
         PasswordResetConfirmView.as_view(success_url='/'), name='password_reset_confirm'),
    path('password/done/', PasswordResetCompleteView.as_view(),
         {'extra_context': {'login_url': '/user/login'}},
         name='password_reset_complete'),
    path('settings/up/', views.SettingsUpView.as_view(), name='settings'),
    path('levels/', views.levels, name='levels'),
    path('profile/', views.SettingsUpView.as_view(), name='profile'),
    path('members/', views.Members.as_view(), name='members'),
    path('user/delete', views.delete, name='delete')
]
