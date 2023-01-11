# -*- coding: utf-8 -*-

from django.contrib.auth import views as django_auth_views
from django.urls import path
from oauth2_provider import views as oauth2_views

from payouts.views import no_agent_error_view
from users.views.main_views import CallbackURLEdit

from . import views

app_name = 'users'


client_urls = [
    path('clients/', views.Clients.as_view(), name='clients'),
    path('client/creation/', views.SuperAdminRootSetup.as_view(), name='add_client'),
    path(
        'client/delete/<str:username>/',
        views.SuperAdminCancelsRootSetupView.as_view(),
        name='delete_client',
    ),
    # 'Adding agents' -url- to the clients is at the disb. app urlpatterns
    path(
        'client/fees-setup/<token>/', views.ClientFeesSetup.as_view(), name='add_fees'
    ),
    path(
        'fees-profile/',
        views.SuperAdminFeesProfileTemplateView.as_view(),
        name='super_fees_profile',
    ),
    path(
        'client/fees-setup/edit/<str:username>/',
        views.CustomClientFeesProfilesUpdateView.as_view(),
        name='update_fees',
    ),
    path(
        'client/fees-setup/update/<str:username>/',
        views.ClientFeesUpdate.as_view(),
        name='update_fees_profile',
    ),
    path('client/toggle/', views.toggle_client, name='toggle'),
]

super_and_root_urls = [
    path('members/', views.Members.as_view(), name='members'),
    path('user/delete/', views.UserDeleteView.as_view(), name='delete'),
    path('settings/branding/', views.EntityBranding.as_view(), name='entity_branding'),
]

support_urls = [
    path('support/home/', views.SupportHomeView.as_view(), name='support_home'),
    path(
        'support/documents/<username>/',
        views.DocumentsForSupportListView.as_view(),
        name='documents_list',
    ),
    path(
        'support/documents/<username>/<doc_id>/',
        views.DocumentForSupportDetailView.as_view(),
        name='doc_detail',
    ),
    path('support/', views.SupportUsersListView.as_view(), name='support'),
    path(
        'support/creation/',
        views.SuperAdminSupportSetupCreateView.as_view(),
        name='add_support',
    ),
    path(
        'support/clients/',
        views.ClientsForSupportListView.as_view(),
        name='support_clients_list',
    ),
    path(
        'support/clients/Credentials',
        views.OnboardingNewInstantAdmin.as_view(),
        name='support_clients_credentials',
    ),
    path(
        'support/clients/Credentials/<client_id>',
        views.ClientCredentialsDetails.as_view(),
        name='support_clients_credentials_details',
    ),
]

onboard_user_urls = [
    path(
        'onboard-user/home/',
        views.OnbooardUserHomeView.as_view(),
        name='onboard_user_home',
    ),
    path('onboard-user/', views.OnboardUsersListView.as_view(), name='onboard_user'),
    path(
        'onboard-user/creation/',
        views.SuperAdminOnboardSetupCreateView.as_view(),
        name='add_onboard_user',
    ),
]

supervisor_user_urls = [
    path(
        'supervisor/home/',
        views.SupervisorUserHomeView.as_view(),
        name='supervisor_home',
    ),
    path('supervisor/', views.SupervisorUsersListView.as_view(), name='supervisor'),
    path(
        'supervisor/creation/',
        views.SuperAdminSupervisorSetupCreateView.as_view(),
        name='add_supervisor_user',
    ),
    path(
        'supervisor/reactivate_support_user',
        views.SupervisorReactivateSupportView.as_view(),
        name='reactivate_support_user',
    ),
]

disbursement_setups_urls = [
    path(
        'setting-up/disbursement-pin',
        views.PinFormView.as_view(),
        name='setting-disbursement-pin',
    ),
    path(
        'setting-up/disbursement-makers',
        views.MakerFormView.as_view(),
        name='setting-disbursement-makers',
    ),
    path(
        'setting-up/disbursement-levels',
        views.LevelsFormView.as_view(),
        name='setting-disbursement-levels',
    ),
    path(
        'setting-up/disbursement-checkers',
        views.CheckerFormView.as_view(),
        name='setting-disbursement-checkers',
    ),
    path(
        'setting-up/disbursement-formats',
        views.CategoryFormView.as_view(),
        name='setting-disbursement-formats',
    ),
    path('members/maker/add/', views.AddMakerView.as_view(), name='add_maker'),
    path('members/checker/add/', views.AddCheckerView.as_view(), name='add_checker'),
    path('levels/', views.LevelsView.as_view(), name='levels'),
    path('change_pin/', views.change_pin_view, name='change_pin'),
]

instant_urls = [
    path('members/viewer/add/', views.ViewerCreateView.as_view(), name='add_viewer'),
    path(
        'members/api-checker/add/',
        views.APICheckerCreateView.as_view(),
        name='add_api_checker',
    ),
]

password_handling_urls = [
    path('change_password/<user>/', views.change_password, name="change_password"),
    path(
        'forgot-password/', views.ForgotPasswordView.as_view(), name="forgot_password"
    ),
    path('password/reset/', views.PasswordResetView.as_view(), name='password_reset'),
    path(
        'password/reset/done/',
        django_auth_views.PasswordResetDoneView.as_view(),
        name='password_reset_done',
    ),
    path(
        'password/reset/<uidb64>/<token>/',
        django_auth_views.PasswordResetConfirmView.as_view(
            success_url='/', template_name='users/password_reset_confirm.html'
        ),
        name='password_reset_confirm',
    ),
    path(
        'password/done/',
        django_auth_views.PasswordResetCompleteView.as_view(),
        {'extra_context': {'login_url': '/user/login'}},
        name='password_reset_complete',
    ),
]

oauth2_provider_urls = [
    path("api/secure/o/token/", oauth2_views.TokenView.as_view(), name="oauth2_token"),
    path(
        "oauth2/keys/<username>/",
        views.OAuth2ApplicationDetailView.as_view(),
        name="oauth2_detail",
    ),
]

sessions_urls = [
    path('sessions/', views.SessionListView.as_view(), name='session_list'),
    path(
        'sessions/other/delete/',
        views.SessionDeleteOtherView.as_view(),
        name='session_delete_other',
    ),
    path(
        'sessions/<str:pk>/delete/',
        views.SessionDeleteView.as_view(),
        name='session_delete',
    ),
]

system_urls = [
    path(
        'creation/admin/<token>/',
        views.OnboardingNewMerchant.as_view(),
        name='creation_admin',
    ),
]

urlpatterns = [
    path('user/login/', views.login_view, name='user_login_view'),
    path('user/logout/', views.ourlogout, name='logout'),
    path('user/no-agent/', no_agent_error_view, name='no_agent_error'),
    path('account/token/', views.OTPLoginView.as_view(), name='otp_login'),
    path('redirect/', views.RedirectPageView.as_view(), name='redirect'),
    path('profile/<username>/', views.ProfileView.as_view(), name='profile'),
    path(
        'profile/edit/<username>/',
        views.ProfileUpdateView.as_view(),
        name='edit_profile',
    ),
    path(
        'callback/edit/<username>/',
        CallbackURLEdit.as_view(),
        name='api_viewer_callback',
    ),
]


urlpatterns += client_urls
urlpatterns += super_and_root_urls
urlpatterns += support_urls
urlpatterns += onboard_user_urls
urlpatterns += supervisor_user_urls
urlpatterns += disbursement_setups_urls
urlpatterns += instant_urls
urlpatterns += password_handling_urls
urlpatterns += oauth2_provider_urls
urlpatterns += sessions_urls
urlpatterns += system_urls
