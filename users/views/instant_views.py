# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse_lazy
from django.views.generic import CreateView

from users.forms import ViewerUserCreationModelForm
from users.mixins import UserWithInstantOnboardingPermissionRequired
from users.models import InstantAPIViewerUser


class ViewerCreateView(UserWithInstantOnboardingPermissionRequired, CreateView):
    """
    Create View for root from instant family to create new viewer users
    """

    model = InstantAPIViewerUser
    form_class = ViewerUserCreationModelForm
    template_name = "instant_cashin/add_member.html"
    success_url = reverse_lazy("users:members")

    def get_form_kwargs(self):
        """
        pass request to form kwargs
        """
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        kwargs["page_title"] = "New Viewer"
        kwargs["form_title"] = "Add Viewer User"
        return super().get_context_data(**kwargs)
