# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView as AbstractPasswordResetView
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.views.generic import FormView

from ..forms import ForgotPasswordForm, PasswordChangeForm, SetPasswordForm


class ForgotPasswordView(FormView):
    """
    View that provides reset password functionality
    """

    form_class = ForgotPasswordForm
    template_name = 'users/forget-password.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Common attributes between GET and POST methods
        """
        self.template_name = 'users/vodafone_forgot_password.html' \
            if "vodafone" in request.get_host() else 'users/forget-password.html'
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """called when form is valid"""
        if form.user:
            form.send_email()
        context = self.get_context_data()
        context['success'] = True
        context['form'] = self.form_class()
        return render(self.request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests: instantiate a form instance with the passed
        POST variables and then check if it's valid.
        """
        form = self.form_class(request.POST)
        if form.is_valid():
            return self.form_valid(form)

        return self.form_invalid(form)


class PasswordResetView(AbstractPasswordResetView):
    """
    View for handling password reset functionality
    """

    success_url = reverse_lazy('users:password_reset_done')


@login_required
def change_password(request, user):
    """
    View for changing or creating password.
    If user already has password then he must enter old one.
    Else enter new password.
    """
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
    return HttpResponseRedirect(reverse('users:user_login_view'))
