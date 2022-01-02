# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models import Q
from django.views.generic import ListView, TemplateView, CreateView
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect

from ..mixins import (
    SuperRequiredMixin, OnboardUserRequiredMixin
)
from ..forms import OnboardUserCreationForm
from ..models import (
    OnboardUser, OnboardUserSetup
)

class OnbooardUserHomeView(OnboardUserRequiredMixin, TemplateView):
    """
    Template view for onboard users home page
    """

    template_name = 'onboard/home.html'


class OnboardUsersListView(SuperRequiredMixin, ListView):
    """
    List onboard users related to the currently logged in super admin
    Search for onboard users by username, email or mobile no by "search" query parameter.
    """

    model = OnboardUserSetup
    paginate_by = 6
    context_object_name = 'onboard_users_setups'
    template_name = 'onboard/list.html'

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(user_created=self.request.user)

        if self.request.GET.get("search"):
            search = self.request.GET.get("search")
            return qs.filter(Q(onboard_user__username__icontains=search) |
                             Q(onboard_user__email__icontains=search) |
                             Q(onboard_user__mobile_no__icontains=search))

        return qs


class SuperAdminOnboardSetupCreateView(SuperRequiredMixin, CreateView):
    """
    Create view for super admin users to create support users
    """

    model = OnboardUser
    form_class = OnboardUserCreationForm
    template_name = 'onboard/add_onboard_user.html'
    success_url = reverse_lazy('users:onboard_user')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        self.onboard_user = form.save()
        support_setup_dict = {
            'onboard_user': self.onboard_user,
            'user_created': self.request.user
        }
        OnboardUserSetup.objects.create(**support_setup_dict)

        return HttpResponseRedirect(self.success_url)