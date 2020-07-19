# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models import Q
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, TemplateView

from data.models import Doc

from ..forms import SupportUserCreationForm
from ..mixins import SuperRequiredMixin, SupportUserRequiredMixin, SupportOrRootOrMakerUserPassesTestMixin
from ..models import Client, SupportSetup, SupportUser, RootUser


class SuperAdminSupportSetupCreateView(SuperRequiredMixin, CreateView):
    """
    Create view for super admin users to create support users
    """

    model = SupportUser
    form_class = SupportUserCreationForm
    template_name = 'support/add_support.html'
    success_url = reverse_lazy('users:support')

    def form_valid(self, form):
        self.support_user = form.save()
        support_setup_dict = {
            'support_user': self.support_user,
            'user_created': self.request.user,
            'can_onboard_entities': form.cleaned_data['can_onboard_entities']
        }
        SupportSetup.objects.create(**support_setup_dict)

        return HttpResponseRedirect(self.success_url)


class SupportUsersListView(SuperRequiredMixin, ListView):
    """
    List support users related to the currently logged in super admin
    Search for support users by username, email or mobile no by "search" query parameter.
    """

    model = SupportSetup
    paginate_by = 6
    context_object_name = 'supporters'
    template_name = 'support/list.html'

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(user_created=self.request.user)

        if self.request.GET.get("search"):
            search = self.request.GET.get("search")
            return qs.filter(Q(support_user__username__icontains=search) |
                             Q(support_user__email__icontains=search) |
                             Q(support_user__mobile_no__icontains=search))

        return qs


class SupportHomeView(SupportUserRequiredMixin, TemplateView):
    """
    Template view for support users home page
    """

    template_name = 'support/home.html'


class ClientsForSupportListView(SupportUserRequiredMixin, ListView):
    """
    List view for retreiving all clients users to the support user
    """

    model = Client
    paginate_by = 6
    context_object_name = 'clients'
    template_name = 'support/clients.html'

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(creator=self.request.user.my_setups.user_created)

        if self.request.GET.get('search'):
            search_key = self.request.GET.get('search')
            return qs.filter(Q(client__username__icontains=search_key) |
                             Q(client__mobile_no__icontains=search_key) |
                             Q(client__email__icontains=search_key))

        return qs


class DocumentsForSupportListView(SupportUserRequiredMixin,
                                  SupportOrRootOrMakerUserPassesTestMixin,
                                  ListView):
    """
    Lists disbursement documents uploaded by specific Admin's members.
    """

    model = Doc
    paginate_by = 10
    context_object_name = 'documents'
    template_name = 'support/documents_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['admin'] = self.kwargs['username']
        return context

    def get_queryset(self, queryset=None):
        admin = RootUser.objects.get(username=self.kwargs['username'])
        return Doc.objects.filter(owner__hierarchy=admin.hierarchy)
