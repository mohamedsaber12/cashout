# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import logging

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, UpdateView

from ..decorators import root_or_superadmin
from ..forms import BrandForm
from ..mixins import RootRequiredMixin, SuperRequiredMixin
from ..models import Brand, Client, SupportSetup, UploaderUser, User

DELETE_USER_VIEW_LOGGER = logging.getLogger("delete_user_view")


class Members(RootRequiredMixin, ListView):
    """
    List checkers and makers related to same root user hierarchy.
    Search members by username, firstname or lastname by "search" query parameter.
    Filter members by type 'maker' or 'checker' by "q" query parameter.
    """

    model = User
    paginate_by = 20
    context_object_name = 'users'
    template_name = 'users/members.html'

    def get_queryset(self):
        if 'disbursement' == self.request.user.get_status(self.request):
            qs = super().get_queryset()
            qs = qs.filter(hierarchy=self.request.user.hierarchy, user_type__in=[1, 2, 5, 6, 7])
            if self.request.GET.get("q"):
                type_of = self.request.GET.get("q")
                if type_of == 'maker':
                    value = 1
                elif type_of == 'checker':
                    value = 2
                else:
                    return qs
                return qs.filter(user_type=value)
        else:
            qs = UploaderUser.objects.filter(hierarchy=self.request.user.hierarchy)

        if self.request.GET.get("search"):
            search = self.request.GET.get("search")
            return qs.filter(Q(username__icontains=search) |
                             Q(first_name__icontains=search) |
                             Q(last_name__icontains=search))
        return qs


class EntityBranding(SuperRequiredMixin, UpdateView):
    """
    View for Entity/Admin branding
    """

    template_name = 'users/entity_branding.html'
    form_class = BrandForm
    model = Brand
    success_url = reverse_lazy('data:main_view')

    def get_object(self, queryset=None):
        return self.request.user.brand

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs


@login_required
@root_or_superadmin
def delete(request):
    """
    Delete any user by user_id
    """

    if request.is_ajax() and request.method == 'POST':
        try:
            data = request.POST.copy()
            if data.get('client'):
                client = Client.objects.get(id=int(data['user_id']))
                user = client.client
                client.delete_client()
            elif data.get('support'):
                support_setup = SupportSetup.objects.get(id=int(data['user_id']))
                user = support_setup.support_user
                User.objects.filter(id=support_setup.support_user.id).delete()
            else:
                user = User.objects.get(id=int(data['user_id']))
                user.delete()
            DELETE_USER_VIEW_LOGGER.debug(
                    f"[USER DELETED]\nSuperAdmin: {request.user.username} deleted user with username: {user.username}"
            )
        except (User.DoesNotExist, Client.DoesNotExist, SupportSetup.DoesNotExist) as e:
            DELETE_USER_VIEW_LOGGER.debug(f"[USER DOES NOT EXIST]\nPassed ID: {data['user_id']}\nError: {e.args[0]}")

        return HttpResponse(content=json.dumps({"valid": "true"}), content_type="application/json")
    else:
        raise Http404()
