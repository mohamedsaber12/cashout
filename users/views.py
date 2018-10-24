from __future__ import print_function, unicode_literals

import datetime
import logging

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser, User
from django.urls import reverse
from django.views.generic import CreateView
from extra_views import CreateWithInlinesView
from extra_views.formsets import ModelFormSetView

from users.forms import (
    SetPasswordForm,
    PasswordChangeForm,
    LevelForm,
    LevelFormSet
)
from data.utils import get_client_ip
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect

from users.models import Levels

LOGIN_LOGGER = logging.getLogger("login")
LOGOUT_LOGGER = logging.getLogger("logout")
UPLOAD_LOGGER = logging.getLogger("upload")
FAILED_LOGIN_LOGGER = logging.getLogger("login_failed")


def ourlogout(request):
    """
    Function that allows users to logout
    """
    if isinstance(request.user, AnonymousUser):
        return HttpResponseRedirect(reverse('users:user_login_view'))
    now = datetime.datetime.now()
    LOGOUT_LOGGER.debug(
        '%s logged out at %s from IP Address %s' % (
            request.user.username, now, get_client_ip(request)))
    request.user.is_otp_verified = False
    request.user.save()

    logout(request)
    response = HttpResponseRedirect(reverse('users:user_login_view'))
    response.delete_cookie('otp_checked')
    return response


def login_view(request):
    """
    Function that allows users to login
    """
    if request.user.is_authenticated:
        return redirect('data:main_view')
    now = datetime.datetime.now()
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        if user:
            if user.is_active:
                login(request, user)
                IP = get_client_ip(request)
                LOGIN_LOGGER.debug(
                    'Logged in ' + str(now) + ' %s with IP Address: %s' % (
                        request.user, IP))
                return HttpResponseRedirect(reverse('data:main_view'))
            else:
                return HttpResponse("Your account has been disabled")
        else:
            # Bad login details were provided. So we can't log the user in.
            FAILED_LOGIN_LOGGER.debug(
                'Failed Login Attempt %s at %s from IP Address %s' % (
                    username, str(now), get_client_ip(request)))
            return render(request, 'data/login.html', {'error_invalid': 'Invalid login details supplied.'})
    else:
        return render(request, 'data/login.html')


@login_required
def change_password(request, user):
    context = {}
    if request.method == 'GET':
        if request.user.has_usable_password():
            form = PasswordChangeForm(request)
        else:
            form = SetPasswordForm(request)
        context['form'] = form
        return render(request, 'data/change_password.html', context=context)

    if request.user.has_usable_password():
        form = PasswordChangeForm(request.user, request.POST)
    else:
        form = SetPasswordForm(request.user, request.POST)

    if not form.is_valid():
        context['form'] = form
        return render(request, 'data/change_password.html', context=context)

    form.save()
    context['form'] = form
    context['MESSAGE'] = "Password changed successfully"
    if context['MESSAGE'] is "Password changed successfully":
        return HttpResponseRedirect(reverse('users:user_login_view'))

    return render(request, 'data/change_password.html', context)


class LevelCreationView(CreateView):
    model = Levels
    template_name = 'users/add_levels.html'
    form_class = LevelForm

    def get(self, request, *args, **kwargs):
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        levelformset = LevelFormSet()
        return self.render_to_response(
            self.get_context_data(form=form,
                                  levelformset=levelformset,
                                  )
        )

    def post(self, request, *args, **kwargs):
        import ipdb; ipdb.set_trace()


def test(request):
    return render(request, 'new_base.html', context={})


class UserInline(CreateWithInlinesView):
    model = User
    fields = '__all__'
    template_name = 'test.html'
