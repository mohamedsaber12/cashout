# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, resolve_url
from django.urls import reverse_lazy
from django.utils.timezone import now
from django.views.generic import DeleteView, ListView, View
from django.views.generic.edit import DeletionMixin
from user_sessions.models import Session


class SessionMixin(object):
    def get_queryset(self):
        return self.request.user.session_set.filter(expire_date__gt=now()).order_by('-last_activity')


class SessionListView(LoginRequiredMixin, SessionMixin, ListView):
    """
    View for listing a user's own sessions.

    This view shows list of a user's currently active sessions. You can
    override the template by providing your own template at
    `users/session_list.html`.
    """

    model = Session
    template_name = 'users/session_list.html'
    context_object_name = 'sessions_list'

    def get_context_data(self, **kwargs):
        kwargs['session_key'] = self.request.session.session_key
        return super().get_context_data(**kwargs)


class SessionDeleteView(LoginRequiredMixin, SessionMixin, DeleteView):
    """
    View for deleting a user's own session.

    This view allows a user to delete an active session. For example log
    out a session from a computer at the local library or a friend's place.
    """
    def delete(self, request, *args, **kwargs):
        if kwargs['pk'] == request.session.session_key:
            logout(request)
            next_page = getattr(settings, 'LOGIN_URL', '/')
            return redirect(resolve_url(next_page))
        return super(SessionDeleteView, self).delete(request, *args, **kwargs)

    def get_success_url(self):
        return str(reverse_lazy('users:session_list'))


class SessionDeleteOtherView(LoginRequiredMixin, SessionMixin, DeletionMixin, View):
    """
    View for deleting all user's sessions but the current.

    This view allows a user to delete all other active session. For example
    log out all sessions from a computer at the local library or a friend's
    place.
    """
    def get_object(self):
        return super(SessionDeleteOtherView, self).get_queryset().exclude(session_key=self.request.session.session_key)

    def get_success_url(self):
        return str(reverse_lazy('users:session_list'))
