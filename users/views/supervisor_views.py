# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.db.models import Q
from django.views.generic import ListView, TemplateView, CreateView
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.views import View


from ..mixins import (
    SuperRequiredMixin, SupervisorUserRequiredMixin, UserOwnsMemberRequiredMixin
)
from ..models import (
    SupervisorUser, SupervisorSetup, SupportSetup, User
)
from ..forms import SupervisorUserCreationForm

class SupervisorUserHomeView(SupervisorUserRequiredMixin, TemplateView):
    """
    Template view for supervisor users home page
    """

    template_name = 'supervisor/home.html'


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

class SupervisorReactivateSupportView(UserOwnsMemberRequiredMixin, View):
    """
    reactivate support user view
    """

    def post(self, request, *args, **kwargs):
        if request.is_ajax():
            try:
                data = request.POST.copy()
                if data.get('support'):
                    support_setup = SupportSetup.objects.get(id=int(data['user_id']))
                    user = support_setup.support_user
                    if not self.request.user.check_password(data.get('password')):
                        return HttpResponse(
                            content=json.dumps({"error": "Invalid Password"}),
                            content_type="application/json"
                        )
                    user.is_active = True
                    user.save()
            except SupportSetup.DoesNotExist:
                return HttpResponse(
                    content=json.dumps({"error": "Support User Not Exist"}),
                    content_type="application/json"
                )

            return HttpResponse(content=json.dumps({"valid": "true"}), content_type="application/json")

        raise Http404
