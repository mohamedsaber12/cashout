from __future__ import print_function, unicode_literals

import logging

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, UpdateView
from django.views.generic.edit import FormView
from ratelimit.decorators import ratelimit
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework_expiring_authtoken.views import ObtainExpiringAuthToken

from data.utils import get_client_ip

from ..forms import OTPTokenForm, ProfileEditForm
from ..models import User

LOGIN_LOGGER = logging.getLogger("login")
LOGOUT_LOGGER = logging.getLogger("logout")
FAILED_LOGIN_LOGGER = logging.getLogger("login_failed")


class ProfileView(DetailView):
    """
    User profile details view.
    """

    model = User
    template_name = 'users/profile.html'

    def get_object(self, queryset=None):
        return get_object_or_404(User, username=self.kwargs['username'])


class ProfileUpdateView(UpdateView):
    """
    User profile update view.
    """

    model = User
    template_name = 'users/profile_update.html'
    form_class = ProfileEditForm

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
    """

    """

    template_name = 'users/redirect_page.html'

    def get(self, request, *args, **kwargs):
        if not (request.user.is_upmaker or (request.user.is_root and request.user.data_type() == 3)):
            return redirect('/')
        status = request.GET.get('status', None)
        if status is not None and status in ['disbursement', 'collection']:
            request.session['status'] = status
            return redirect(reverse(f'data:{status}_home'))

        return render(request, self.template_name, {})


class ExpiringAuthToken(ObtainExpiringAuthToken):
    """
    Customizes AuthToken expiry of django rest framework
    """

    def post(self, request):
        """Respond to POSTed username/password with token."""
        serializer = AuthTokenSerializer(data=request.data, context={"request": request})

        if serializer.is_valid():
            token, _ = self.model.objects.get_or_create(user=serializer.validated_data['user'])

            if token.expired():
                # If the token is expired, generate a new one.
                token.delete()
                token = self.model.objects.create(user=serializer.validated_data['user'])

            data = {'token': token.key}
            return Response(data)

        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


# @ratelimit(key=lambda g, r: get_client_ip(r), rate='3/5m', method=ratelimit.UNSAFE, block=True)
def login_view(request):
    """
    Function that allows users to login.
    Checkers must do two factor authentication every login but makers don't.
    Non active users can't login.
    """
    user = None

    if request.user.is_authenticated:
        if request.user.is_checker:
            return HttpResponseRedirect(reverse('two_factor:profile'))
        return redirect('data:main_view')
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request=request, username=username, password=password)
        if user and not user.is_instantapichecker:
            if user.is_active:
                login(request, user)
                LOGIN_LOGGER.debug(f"User: {request.user.username} Logged In from IP Address {get_client_ip(request)}")
                if user.is_checker:
                    user.is_totp_verified = False
                    user.save()
                    return HttpResponseRedirect(reverse('two_factor:profile'))

                if user.is_upmaker or (user.is_root and user.data_type() == 3):
                    return HttpResponseRedirect(reverse('users:redirect'))

                return HttpResponseRedirect(reverse('data:main_view'))
            else:
                FAILED_LOGIN_LOGGER.debug(f"""[FAILED LOGIN]
                Failed Attempt from non active user with username: {username} and IP Addr {get_client_ip(request)}""")
                return HttpResponse("Your account has been disabled")
        elif user is not None and user.is_instantapichecker:
            FAILED_LOGIN_LOGGER.debug(f"""[API USER LOGIN ATTEMPT]
            Failed Attempt from instant API user with username: {username} and IP Addr {get_client_ip(request)}""")
            return render(request, 'data/login.html', {'error_invalid': "You're not permitted to login."})
        else:
            # Bad login details were provided. So we can't log the user in.
            FAILED_LOGIN_LOGGER.debug(f"""[FAILED LOGIN]
            Failed Login Attempt from user with username: {username} and IP Address {get_client_ip(request)}""")
            return render(request, 'data/login.html', {'error_invalid': 'Invalid login details supplied.'})
    else:
        return render(request, 'data/login.html')


def ourlogout(request):
    """
    Function that allows users to logout.
    Remove otp verification from user.
    """

    if isinstance(request.user, AnonymousUser):
        return HttpResponseRedirect(reverse('users:user_login_view'))

    LOGOUT_LOGGER.debug(f"User: {request.user.username} Logged Out from IP Address {get_client_ip(request)}")
    request.user.is_totp_verified = False
    request.user.save()
    logout(request)

    return HttpResponseRedirect(reverse('users:user_login_view'))
