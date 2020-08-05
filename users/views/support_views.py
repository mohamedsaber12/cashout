# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models import Q
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.translation import ugettext as _
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView

from data.models import Doc

from ..forms import SupportUserCreationForm
from ..mixins import (
    SuperRequiredMixin, SupportUserRequiredMixin, SupportOrRootOrMakerUserPassesTestMixin,
    UserWithAcceptVFOnboardingPermissionRequired,
)
from ..models import Client, SupportSetup, SupportUser, RootUser


class SuperAdminSupportSetupCreateView(UserWithAcceptVFOnboardingPermissionRequired,
                                       SuperRequiredMixin,
                                       CreateView):
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


class SupportUsersListView(UserWithAcceptVFOnboardingPermissionRequired,
                           SuperRequiredMixin,
                           ListView):
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
    List view for retrieving all clients users to the support user
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
        qs = Doc.objects.filter(owner__hierarchy=admin.hierarchy).prefetch_related('disbursement_txn')

        if self.request.GET.get('search'):
            doc_id = self.request.GET.get('search')
            qs = qs.filter(id__icontains=doc_id)

        return qs


class DocumentForSupportDetailView(SupportUserRequiredMixin,
                                   SupportOrRootOrMakerUserPassesTestMixin,
                                   View):
    """
    Detail view to retrieve every little detail about every document
    """

    def retrieve_doc_status(self, doc_obj):
        """Retrieve doc status given doc object"""

        if doc_obj.validation_process_is_running:
            return 'Validation process is running'
        elif doc_obj.validated_successfully:
            return 'Validated successfully'
        elif doc_obj.validation_failed:
            return 'Validation failure'
        elif doc_obj.disbursement_failed:
            return 'Disbursement failure'
        elif doc_obj.waiting_disbursement:
            return 'Ready for disbursement'
        elif doc_obj.waiting_disbursement_callback:
            return 'Disbursed successfully and waiting for the disbursement callback'
        elif doc_obj.disbursed_successfully:
            return 'Disbursed successfully'

    def dispatch(self, request, *args, **kwargs):
        """Shared attributes between GET and POST methods"""
        self.doc_id = self.kwargs['doc_id']
        self.admin_username = self.kwargs['username']
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Handle GET request to retrieve details for specific document with id"""

        admin = RootUser.objects.get(username=self.admin_username)
        doc = Doc.objects.prefetch_related('disbursement_data', 'disbursement_txn', 'reviews').filter(
                id=self.doc_id, owner__hierarchy=admin.hierarchy
        )

        if not doc.exists():
            raise Http404(_(f"Document with id: {self.doc_id} for {self.admin_username} entity members not found."))

        doc = doc.first()
        context = {
            'doc_obj': doc,
            'reviews': doc.reviews.all() ,
            'doc_status': self.retrieve_doc_status(doc),
            'disbursement_ratio': doc.disbursement_ratio(),
            'is_reviews_completed': doc.is_reviews_completed(),
            'disbursement_records': doc.disbursement_data.all(),
            'disbursement_doc_data': doc.disbursement_txn
        }

        return render(request, 'support/document_details.html', context=context)
