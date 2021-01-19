# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView
from oauth2_provider.models import Application

from users.forms import ViewerUserCreationModelForm, APICheckerUserCreationModelForm
from users.mixins import UserWithInstantOnboardingPermissionRequired
from users.models import InstantAPIViewerUser, InstantAPICheckerUser


class BaseInstantMemberCreateView(UserWithInstantOnboardingPermissionRequired, CreateView):
    """
    Base create view for creating instant members
    """

    template_name = "instant_cashin/add_member.html"
    success_url = reverse_lazy("users:members")

    def get_form_kwargs(self):
        """
        pass request to form kwargs
        """
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs


class ViewerCreateView(BaseInstantMemberCreateView):
    """
    Create View for root from instant family to create new viewer users
    """

    model = InstantAPIViewerUser
    form_class = ViewerUserCreationModelForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        kwargs["page_title"] = "New Viewer"
        kwargs["form_title"] = "Add Viewer User"
        return super().get_context_data(**kwargs)


class APICheckerCreateView(BaseInstantMemberCreateView):
    """
    Create View for root from instant family to create new viewer users
    """

    model = InstantAPICheckerUser
    form_class = APICheckerUserCreationModelForm

    def get_context_data(self, **kwargs):
        kwargs["page_title"] = "New API Checker"
        kwargs["form_title"] = "Add API Checker User"
        return super().get_context_data(**kwargs)


class OAuth2ApplicationDetailView(DetailView):
    """
    View for Retrieving oauth2 application details for specific user
    """

    model = Application
    template_name = "instant_cashin/auth_keys.html"
    context_object_name = "oauth2_app"

    def get_object(self, queryset=None):
        return get_object_or_404(Application, user__username=self.kwargs['username'])
