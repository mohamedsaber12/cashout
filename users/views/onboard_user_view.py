# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models import Q
from django.views.generic import ListView

from ..mixins import (
    SuperRequiredMixin
)
from ..models import (
    OnboardUser, OnboardUserSetup
)


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