from django.contrib.auth import views as django_auth_views
from django.urls import path

from oauth2_provider import views as oauth2_views

from . import views


app_name = 'users'


collection_setups_urls = [
    path('setting-up/collection-collectiondata',
         views.CollectionFormView.as_view(), name='setting-collection-collectiondata'),
    path('setting-up/collection-formats', views.FormatFormView.as_view(), name='setting-collection-formats'),
    path('setting-up/collection-uploader', views.UploaderFormView.as_view(), name='setting-collection-uploader'),
]

client_urls = [
    path('clients/', views.Clients.as_view(), name='clients'),
    path('client/creation/', views.SuperAdminRootSetup.as_view(), name='add_client'),
    # 'Adding agents' -url- to the clients is at the disb. app urlpatterns
    path('client/fees-setup/<token>/', views.ClientFeesSetup.as_view(), name='add_fees'),
    path('client/toggle/', views.toggle_client, name='toggle'),
]

super_and_root_urls = [
    path('members/', views.Members.as_view(), name='members'),
    path('user/delete/', views.delete, name='delete'),
    path('settings/branding/', views.EntityBranding.as_view(), name='entity_branding'),
]

instant_api_urls = [
    path('instant-transactions/', views.InstantTransactionsView.as_view(), name='instant_transactions'),
]

disbursement_setups_urls = [
    path('setting-up/disbursement-pin', views.PinFormView.as_view(), name='setting-disbursement-pin'),
    path('setting-up/disbursement-makers', views.MakerFormView.as_view(), name='setting-disbursement-makers'),
    path('setting-up/disbursement-levels', views.LevelsFormView.as_view(), name='setting-disbursement-levels'),
    path('setting-up/disbursement-checkers', views.CheckerFormView.as_view(), name='setting-disbursement-checkers'),
    path('setting-up/disbursement-formats', views.CategoryFormView.as_view(), name='setting-disbursement-formats'),
    path('members/maker/add/', views.AddMakerView.as_view(), name='add_maker'),
    path('members/checker/add/', views.AddCheckerView.as_view(), name='add_checker'),
    path('levels/', views.LevelsView.as_view(), name='levels'),
]

password_handling_urls = [
    path('change_password/<user>/', views.change_password, name="change_password"),
    path('forgot-password/', views.ForgotPasswordView.as_view(), name="forgot_password"),
    path('password/reset/', views.PasswordResetView.as_view(), name='password_reset'),
    path('password/reset/done/', django_auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password/reset/<uidb64>/<token>/',
         django_auth_views.PasswordResetConfirmView.as_view(
                 success_url='/', template_name='users/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password/done/',
         django_auth_views.PasswordResetCompleteView.as_view(), {'extra_context': {'login_url': '/user/login'}},
         name='password_reset_complete'),
]

oauth2_provider_urls = [
    path("api/secure/o/token/", oauth2_views.TokenView.as_view(), name="oauth2_token"),
]

urlpatterns = [
    path('user/login/', views.login_view, name='user_login_view'),
    path('user/logout/', views.ourlogout, name='logout'),
    path('account/token/', views.OTPLoginView.as_view(), name='otp_login'),
    path('redirect/', views.RedirectPageView.as_view(), name='redirect'),

    path('profile/<username>/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/<username>/', views.ProfileUpdateView.as_view(), name='edit_profile'),
]

urlpatterns += collection_setups_urls
urlpatterns += client_urls
urlpatterns += super_and_root_urls
urlpatterns += instant_api_urls
urlpatterns += disbursement_setups_urls
urlpatterns += password_handling_urls
urlpatterns += oauth2_provider_urls
