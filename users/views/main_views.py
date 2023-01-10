import logging

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, UpdateView
from django.views.generic.edit import FormView
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework_expiring_authtoken.views import ObtainExpiringAuthToken

from users.sso import SSOIntegration

from ..forms import (CallbackURLEditForm, LevelEditForm, OTPTokenForm,
                     ProfileEditForm)
from ..mixins import ProfileOwnerOrMemberRequiredMixin
from ..models import User

LOGIN_LOGGER = logging.getLogger("login")
LOGOUT_LOGGER = logging.getLogger("logout")
FAILED_LOGIN_LOGGER = logging.getLogger("login_failed")


class ProfileView(ProfileOwnerOrMemberRequiredMixin, DetailView):
    """
    User profile details view.
    """

    model = User
    template_name = 'users/profile.html'

    def get_object(self, queryset=None):
        return get_object_or_404(User, username=self.kwargs['username'])


class ProfileUpdateView(ProfileOwnerOrMemberRequiredMixin, UpdateView):
    """
    User profile update view.
    """

    model = User
    template_name = 'users/profile_update.html'
    form_class = ProfileEditForm

    def get_object(self, queryset=None):
        return get_object_or_404(User, username=self.kwargs['username'])


class LevelUpdateView(ProfileOwnerOrMemberRequiredMixin, UpdateView):
    """
    user levels update
    """

    model = User
    template_name = 'users/level_update.html'
    form_class = LevelEditForm

    def get_form_kwargs(self):
        """
        pass request to form kwargs
        """
        kwargs = super().get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs

    def get_success_url(self):
        """Redirect URL after saving edits successfully"""
        return reverse("users:members")

    def get_object(self, queryset=None):
        return get_object_or_404(User, username=self.kwargs['username'])


class OTPLoginView(FormView):
    """
    View for OTP login for checker users
    """

    template_name = 'two_factor/login.html'
    success_url = '/'

    def post(self, request, *args, **kwargs):
        form = OTPTokenForm(data=request.POST, user=self.request.user)
        if form.is_valid():
            request.user.is_totp_verified = True
            request.user.save()
            return self.form_valid(form)
        return self.form_invalid(form)

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return OTPTokenForm(user=self.request.user)


class RedirectPageView(View):
    """ """

    template_name = 'users/redirect_page.html'

    def get(self, request, *args, **kwargs):
        if not (
            request.user.is_upmaker
            or (request.user.is_root and request.user.data_type() == 3)
        ):
            return redirect('/')
        status = request.GET.get('status', None)
        if status is not None and status in ['disbursement', 'collection']:
            request.session['status'] = status
            return redirect(reverse(f'data:e_wallets_home'))

        return render(request, self.template_name, {})


class ExpiringAuthToken(ObtainExpiringAuthToken):
    """
    Customizes AuthToken expiry of django rest framework
    """

    def post(self, request):
        """Respond to POSTed username/password with token."""
        serializer = AuthTokenSerializer(
            data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            token, _ = self.model.objects.get_or_create(
                user=serializer.validated_data['user']
            )

            if token.expired():
                # If the token is expired, generate a new one.
                token.delete()
                token = self.model.objects.create(
                    user=serializer.validated_data['user']
                )

            data = {'token': token.key}
            return Response(data)

        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


def login_view(request):
    """
    Function that allows users to login.
    Checkers must do two factor authentication every login but makers don't.
    Non active users can't login.
    """
    context = {}
    login_template = (
        'data/vodafone_login.html'
        if "vodafone" in request.get_host()
        else 'data/login.html'
    )
    user = None

    if request.user.is_authenticated:

        # this is special case based on business demand for prevent \
        # two factor authentication for this admin => Careem_Admin
        if request.user.username == 'Careem_Admin':
            return redirect('data:main_view')

        if (
            request.user.is_vodafone_default_onboarding
            or request.user.is_banks_standard_model_onboaring
            or request.user.is_accept_vodafone_onboarding
            and request.user.is_checker
            or request.user.is_vodafone_facilitator_onboarding
            and request.user.is_checker
        ):
            if not request.user.is_superuser and (
                request.user.is_checker
                or request.user.is_root
                or request.user.is_superadmin
            ):
                return HttpResponseRedirect(reverse('two_factor:profile'))
        return redirect('data:main_view')
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        # user = authenticate(request=request, username=username, password=password)
        sso = SSOIntegration()
        user = sso.authenticate(username, password)
        if user and not user.is_instantapichecker:
            if user.is_active:
                login(
                    request, user, backend="django.contrib.auth.backends.ModelBackend"
                )
                LOGIN_LOGGER.debug(f"[message] [LOGIN] [{request.user}] -- ")

                # this is special case based on business demand for prevent \
                # two factor authentication for this admin => Careem_Admin
                if request.user.username == 'Careem_Admin':
                    return HttpResponseRedirect(reverse('data:main_view'))

                if (
                    request.user.is_vodafone_default_onboarding
                    or request.user.is_banks_standard_model_onboaring
                    or request.user.is_accept_vodafone_onboarding
                    and request.user.is_checker
                    or request.user.is_vodafone_facilitator_onboarding
                    and request.user.is_checker
                ):
                    if not request.user.is_superuser and (
                        user.is_checker or user.is_root or user.is_superadmin
                    ):
                        user.is_totp_verified = False
                        user.save()
                        return HttpResponseRedirect(reverse('two_factor:profile'))

                if user.is_upmaker or (user.is_root and user.data_type() == 3):
                    return HttpResponseRedirect(reverse('users:redirect'))

                return HttpResponseRedirect(reverse('data:main_view'))
            else:
                FAILED_LOGIN_LOGGER.debug(
                    f"[message] [FAILED LOGIN] [{username}] -- "
                    f"Failed Attempt from non active user with username: {username}"
                )
                return HttpResponse("Your account has been disabled")
        elif user is not None and user.is_instantapichecker:
            FAILED_LOGIN_LOGGER.debug(
                f"[message] [API USER LOGIN ATTEMPT] [{username}] -- "
                f"Failed Attempt from instant API user with username: {username}"
            )
            context['error_invalid'] = "You're not permitted to login."
            return render(request, login_template, context=context)
        else:
            # Bad login details were provided. So we can't log the user in.
            FAILED_LOGIN_LOGGER.debug(
                f"[message] [FAILED LOGIN] [anonymous] -- Failed Login Attempt from user with username: {username}"
            )
            context['error_invalid'] = 'Invalid login details supplied.'
            return render(request, login_template, context=context)
    else:
        idms_token = request.COOKIES.get("IDMS_TOKEN")
        if idms_token:
            sso = SSOIntegration()
            user_found, user_obj = sso.get_user_with_idms_access_token(idms_token)
            if user_found:
                login(
                    request,
                    user_obj,
                    backend="django.contrib.auth.backends.ModelBackend",
                )
        return render(request, login_template, context=context)


def ourlogout(request):
    """
    Function that allows users to logout.
    Remove otp verification from user.
    """

    if isinstance(request.user, AnonymousUser):
        return HttpResponseRedirect(reverse('users:user_login_view'))

    LOGOUT_LOGGER.debug(f"[message] [LOGOUT] [{request.user}] -- ")
    request.user.is_totp_verified = False
    request.user.save()
    logout(request)

    return HttpResponseRedirect(reverse('users:user_login_view'))


class CallbackURLEdit(UpdateView):

    model = User
    template_name = 'users/callback_url.html'
    form_class = CallbackURLEditForm

    def get_object(self, queryset=None):
        user = get_object_or_404(User, username=self.kwargs['username'])
        return user.root.root

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.save()
        return redirect(
            reverse(
                "users:api_viewer_callback",
                kwargs={'username': self.request.user.username},
            )
        )
