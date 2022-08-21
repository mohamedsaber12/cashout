# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.utils.translation import gettext_lazy as _
from django.utils.timezone import datetime, make_aware

from .forms import BudgetAdminModelForm
from .functions import custom_budget_logger
from .mixins import CustomInlineAdmin
from .models import Budget, CallWalletsModerator, FeeSetup, TopupRequest, TopupAction
from simple_history.admin import SimpleHistoryAdmin
from django.core.exceptions import PermissionDenied
from django import http
from django.contrib.admin.utils import unquote
from django.conf import settings
from django.utils.text import capfirst
import django
from django.core.paginator import Paginator

if django.VERSION < (2,):
    from django.utils.encoding import force_text as force_str
else:
    from django.utils.encoding import force_str

from users.models import InstantAPICheckerUser, User
from rangefilter.filter import DateRangeFilter


USER_NATURAL_KEY = tuple(key.lower() for key in settings.AUTH_USER_MODEL.split(".", 1))


@admin.register(CallWalletsModerator)
class CallWalletsModeratorAdmin(admin.ModelAdmin):
    """
    Customize the list view of the call wallets moderator model
    """

    list_display = [
        "user_created",
        "disbursement",
        "instant_disbursement",
        "change_profile",
        "set_pin",
        "user_inquiry",
        "balance_inquiry",
    ]
    list_filter = [
        "change_profile",
        "set_pin",
        "user_inquiry",
        "balance_inquiry",
        "disbursement",
        "instant_disbursement",
    ]
    search_fields = ["user_created__username"]


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    """
    Add LogEntry built-in model to the admin panel and customize its view.
    """

    readonly_fields = [
        "action_flag",
        "action_time",
        "user",
        "content_type",
        "object_repr",
        "change_message",
    ]
    exclude = ["object_id"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class FeeSetupAdmin(CustomInlineAdmin):
    """
    FeeSetup inline Admin model for handling fees for every entity budget
    """

    model = FeeSetup
    extra = 0


@admin.register(Budget)
class BudgetAdmin(SimpleHistoryAdmin):
    """
    Budget Admin model for the Budget model
    """

    object_history_template = "admin/list_history.html"
    form = BudgetAdminModelForm
    inlines = [FeeSetupAdmin]
    list_filter = ["updated_at", "created_at", "created_by"]
    list_display = [
        "disburser",
        "current_balance",
        "total_disbursed_amount",
        "updated_at",
    ]
    readonly_fields = [
        "total_disbursed_amount",
        "updated_at",
        "created_at",
        "created_by",
        "current_balance",
    ]
    search_fields = ["disburser__username", "created_by__username"]
    ordering = ["-updated_at", "-created_at"]
    history_list_display = ["current_balance"]

    fieldsets = (
        (_("Users Details"), {"fields": ("disburser", "created_by")}),
        (
            _("Budget Amount Details"),
            {
                "fields": (
                    "total_disbursed_amount",
                    "current_balance",
                    "add_new_amount",
                    "fx_rate",
                    "updated_at",
                    "created_at",
                )
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if not request.user.is_superuser or not request.user.is_superadmin:
            return readonly_fields + self.list_display
        return readonly_fields

    def has_add_permission(self, request):
        if not request.user.is_superuser or not request.user.is_superadmin:
            return False
        return True

    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

    def save_model(self, request, obj, form,change):
        if not request.user.is_superuser or not request.user.is_superadmin:
            raise PermissionError(
                _("Only super users allowed to create/update at this table.")
            )
        obj.created_by = request.user
        obj.save()
        custom_budget_logger(
            obj.disburser,
            f"New added amount: {form.cleaned_data['add_new_amount']} LE",
            obj.created_by,
            head="[message] [update from django admin]",
        )

    def history_view(self, request, object_id, extra_context=None):
        """The 'history' admin view for this model."""
        request.current_app = self.admin_site.name
        model = self.model
        opts = model._meta
        app_label = opts.app_label
        pk_name = opts.pk.attname
        history = getattr(model, model._meta.simple_history_manager_attribute)
        object_id = unquote(object_id)
        action_list = history.filter(**{pk_name: object_id})
        if not isinstance(history.model.history_user, property):
            # Only select_related when history_user is a ForeignKey (not a property)
            action_list = action_list.select_related("history_user")
        history_list_display = getattr(self, "history_list_display", [])
        # If no history was found, see whether this object even exists.
        try:
            obj = self.get_queryset(request).get(**{pk_name: object_id})
        except model.DoesNotExist:
            try:
                obj = action_list.latest("history_date").instance
            except action_list.model.DoesNotExist:
                raise http.Http404

        if not self.has_change_permission(request, obj):
            raise PermissionDenied

        # Set attribute on each action_list entry from admin methods
        for history_list_entry in history_list_display:
            value_for_entry = getattr(self, history_list_entry, None)
            if value_for_entry and callable(value_for_entry):
                for list_entry in action_list:
                    setattr(list_entry, history_list_entry, value_for_entry(list_entry))

        content_type = self.content_type_model_cls.objects.get_by_natural_key(
            *USER_NATURAL_KEY
        )
        admin_user_view = "admin:%s_%s_change" % (
            content_type.app_label,
            content_type.model,
        )
        # filter by history_user
        history_user = request.GET.get("history_user", None)
        if history_user:
            action_list = action_list.filter(history_user=history_user)

        # filter by history date
        start_history_date = request.GET.get("history_date__range__gte", None)
        end_history_date = request.GET.get("history_date__range__lte", None)

        if start_history_date:
            first_day = datetime(
                year=int(start_history_date.split("-")[0]),
                month=int(start_history_date.split("-")[1]),
                day=int(start_history_date.split("-")[2]),
            )
            first_day = make_aware(first_day)
            action_list = action_list.filter(history_date__gte=first_day)
        if end_history_date:
            last_day = datetime(
                year=int(end_history_date.split("-")[0]),
                month=int(end_history_date.split("-")[1]),
                day=int(end_history_date.split("-")[2]),
                hour=23,
                minute=59,
                second=59,
            )
            last_day = make_aware(last_day)
            action_list = action_list.filter(history_date__lte=last_day)

        page = request.GET.get("page", 1)
        paginator = Paginator(action_list, 30)
        action_list = paginator.get_page(page)

        # convert query string to dictionary
        from urllib.parse import parse_qs

        query_string_dict = parse_qs(request.META["QUERY_STRING"])

        query_string_date = ""
        if query_string_dict.get("history_date__range__gte", None):
            query_string_date = (
                query_string_date
                + "history_date__range__gte="
                + query_string_dict.get("history_date__range__gte")[0]
            )
        if (
            query_string_dict.get("history_date__range__lte", None)
            and query_string_date != ""
        ):
            query_string_date = (
                query_string_date
                + "&history_date__range__lte="
                + query_string_dict.get("history_date__range__lte")[0]
            )
        elif query_string_dict.get("history_date__range__lte", None):
            query_string_date = (
                query_string_date
                + "history_date__range__lte="
                + query_string_dict.get("history_date__range__lte")[0]
            )

        if settings.DEBUG:
            admin_url_key = "admin"
        else:
            admin_url_key = "secure-portal"

        context = {
            "title": self.history_view_title(obj),
            "action_list": action_list,
            "module_name": capfirst(force_str(opts.verbose_name_plural)),
            "object": obj,
            "root_path": getattr(self.admin_site, "root_path", None),
            "app_label": app_label,
            "opts": opts,
            "admin_user_view": admin_user_view,
            "history_list_display": history_list_display,
            "revert_disabled": self.revert_disabled,
            "users_can_filter": [
                obj.disburser,
                *list(InstantAPICheckerUser.objects.filter(root=obj.disburser)),
                *list(User.objects.filter(is_staff=True)),
            ],
            "query_string_date": query_string_date,
            "admin_url_key": admin_url_key,
        }
        context.update(self.admin_site.each_context(request))
        context.update(extra_context or {})
        extra_kwargs = {}
        return self.render_history_view(
            request, self.object_history_template, context, **extra_kwargs
        )


@admin.register(TopupRequest)
class TopupRequestAdmin(admin.ModelAdmin):
    """
    Customize the list view of the call topup requests model
    """

    list_display = ["client", "amount", "currency", "created_at", "updated_at"]
    list_filter = [
        "client",
        "currency",
        ("created_at", DateRangeFilter),
    ]


@admin.register(TopupAction)
class TopupActionAdmin(admin.ModelAdmin):
    """
    Customize the list view of the call topup requests model
    """

    list_display = [
        "client",
        "amount",
        "fx_ratio_amount",
        "balance_before",
        "balance_after",
        "created_at",
    ]
    list_filter = [
        "client",
        ("created_at", DateRangeFilter),
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request,obj=None):
        return False
