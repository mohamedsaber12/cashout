from django.contrib.auth.views import (PasswordChangeDoneView,
                                       PasswordChangeView,
                                       PasswordResetCompleteView,
                                       PasswordResetConfirmView,
                                       PasswordResetDoneView)
from django.urls import path

from users import views

app_name = 'users'

urlpatterns = [
    path('user/login/', views.login_view,
         name='user_login_view'),
    path('user/logout/', views.ourlogout, name='logout'),
    path('forgot-password/', views.ForgotPasswordView.as_view(), name="forgot_password"),
    path('change_password/<user>/', views.change_password, name="change_password"),
    path('password/reset/done/', PasswordResetDoneView.as_view(),
         name='password_reset_done'),
    path('password/reset/', views.PasswordResetView.as_view(),
         name='password_reset_done'),
    path('password/reset/<uidb64>/<token>/',
         PasswordResetConfirmView.as_view(success_url='/', template_name='users/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password/done/', PasswordResetCompleteView.as_view(),
         {'extra_context': {'login_url': '/user/login'}},
         name='password_reset_complete'),
   
    path('setting-up/dibursement-pin', views.PinFormView.as_view(),
         name='setting-dibursement-pin'),
    path('setting-up/dibursement-makers', views.MakerFormView.as_view(),
         name='setting-dibursement-makers'),
    path('setting-up/dibursement-levels', views.LevelsFormView.as_view(),
         name='setting-dibursement-levels'),
    path('setting-up/dibursement-checkers', views.CheckerFormView.as_view(),
         name='setting-dibursement-checkers'),
    path('setting-up/dibursement-formats', views.CategoryFormView.as_view(),
         name='setting-dibursement-formats'),
    path('setting-up/collection-collectiondata', views.CollectionFormView.as_view(),
         name='setting-collection-collectiondata'),
    path('setting-up/collection-formats', views.FormatFormView.as_view(),
         name='setting-collection-formats'),
    path('setting-up/collection-uploader', views.UploaderFormView.as_view(),
         name='setting-collection-uploader'),
    path('levels/', views.LevelsView.as_view(), name='levels'),
    path('profile/<username>/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/<username>/', views.ProfileUpdateView.as_view(), name='edit_profile'),
    path('members/', views.Members.as_view(), name='members'),
    path('members/checker/add/', views.AddCheckerView.as_view(), name='add_checker'),
    path('members/maker/add/', views.AddMakerView.as_view(), name='add_maker'),
    path('user/delete/', views.delete, name='delete'),
    path('client/toggle/', views.toggle_client, name='toggle'),
    path('client/creation/', views.SuperAdminRootSetup.as_view(), name='add_client'),
    path('client/fees-setup/<token>/',
         views.ClientFeesSetup.as_view(), name='add_fees'),
    path('clients/', views.Clients.as_view(), name='clients'),
    path('settings/branding/', views.EntityBranding.as_view(), name='entity_branding'),
    path('account/token/', views.OTPLoginView.as_view(), name='otp_login'),
    path('redirect/', views.RedirectPageView.as_view(), name='redirect')
    

]
