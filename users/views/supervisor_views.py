# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models import Q
from django.views.generic import ListView, TemplateView, CreateView
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect

from ..mixins import (
    SuperRequiredMixin
)
from ..models import (
    SupervisorUser, SupervisorSetup
)
from ..forms import SupervisorUserCreationForm


class SupervisorUsersListView(SuperRequiredMixin, ListView):
    """
    List onboard users related to the currently logged in super admin
    Search for onboard users by username, email or mobile no by "search" query parameter.
    """

    model = SupervisorSetup
    paginate_by = 6
    context_object_name = 'supervisors_setups'
    template_name = 'supervisor/list.html'

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(user_created=self.request.user)

        if self.request.GET.get("search"):
            search = self.request.GET.get("search")
            return qs.filter(Q(onboard_user__username__icontains=search) |
                             Q(onboard_user__email__icontains=search) |
                             Q(onboard_user__mobile_no__icontains=search))

        return qs


class SuperAdminSupervisorSetupCreateView(SuperRequiredMixin, CreateView):
    """
    Create view for super admin users to create support users
    """

    model = SupervisorUser
    form_class = SupervisorUserCreationForm
    template_name = 'supervisor/add_supervisor_user.html'
    success_url = reverse_lazy('users:supervisor')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        self.supervisor_user = form.save()
        supervisor_setup_dict = {
            'supervisor_user': self.supervisor_user,
            'user_created': self.request.user
        }
        SupervisorSetup.objects.create(**supervisor_setup_dict)

        return HttpResponseRedirect(self.success_url)
