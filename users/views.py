from __future__ import print_function, unicode_literals

import json
import logging

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser, Permission
from django.contrib.auth.views import PasswordResetView as AbstractPasswordResetView
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import (CreateView, DetailView, ListView, TemplateView, UpdateView)
from django.views.generic.edit import FormView

from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework_expiring_authtoken.models import ExpiringToken
from rest_framework_expiring_authtoken.views import ObtainExpiringAuthToken

from data.forms import CollectionDataForm, FileCategoryFormSet, FormatFormSet
from data.models import FileCategory, Format
from data.utils import get_client_ip
from disb.forms import PinForm
from instant_cashin.models import InstantTransaction

from .decorators import root_or_superadmin
from .forms import (BrandForm, CheckerCreationForm, CheckerMemberFormSet,
                    ClientFeesForm, CustomClientProfilesForm, ForgotPasswordForm, LevelFormSet,
                    MakerCreationForm, MakerMemberFormSet, OTPTokenForm,
                    PasswordChangeForm, ProfileEditForm, RootCreationForm,
                    SetPasswordForm, UploaderMemberFormSet)
from .mixins import (CollectionRootRequiredMixin, InstantReviewerRequiredMixin,
                     DisbursementRootRequiredMixin, RootRequiredMixin, SuperFinishedSetupMixin,
                     SuperOwnsClientRequiredMixin, SuperOwnsCustomizedBudgetClientRequiredMixin, SuperRequiredMixin)
from .models import (Brand, CheckerUser, Client, EntitySetup, Levels, MakerUser, RootUser, Setup, UploaderUser, User)


LOGIN_LOGGER = logging.getLogger("login")
LOGOUT_LOGGER = logging.getLogger("logout")
FAILED_LOGIN_LOGGER = logging.getLogger("login_failed")
SETUP_VIEW_LOGGER = logging.getLogger("setup_view")
DELETE_USER_VIEW_LOGGER = logging.getLogger("delete_user_view")
LEVELS_VIEW_LOGGER = logging.getLogger("levels_view")
ROOT_CREATE_LOGGER = logging.getLogger("root_create")


class PinFormView(DisbursementRootRequiredMixin, FormView):
    template_name = 'users/setting-up-disbursement/pin.html'
    setup = None

    def get(self, request, *args, **kwargs):
        """Handle GET requests: instantiate a blank version of the form."""
        if request.GET.get('q', None) == 'next':
            setup = self.get_setup()
            if setup.pin_setup:
                return HttpResponseRedirect(self.get_success_url())
        return self.render_to_response(self.get_context_data())

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return PinForm(root=self.request.user).get_form()

    def get_context_data(self, **kwargs):
        """update context data"""
        data = super().get_context_data(**kwargs)
        data['form_exist'] = bool(PinForm(root=self.request.user).get_form())
        data['enabled_steps'] = '-'.join(self.get_setup().disbursement_enabled_steps())
        return data

    def post(self, request, *args, **kwargs):
        form = PinForm(request.POST, root=request.user).get_form()
        if form and form.is_valid():
            ok = form.set_pin()
            if not ok:
                return self.form_invalid(form)
            setup = self.get_setup()
            setup.pin_setup = True
            setup.save()
            return self.form_valid(form)
        return self.form_invalid(form)

    def get_setup(self):
        if self.setup is None:
            self.setup = Setup.objects.get(user__hierarchy=self.request.user.hierarchy)
        return self.setup

    def get_success_url(self):
        to_step = self.request.GET.get('to_step', None)
        if to_step == '3':
            return reverse('users:setting-disbursement-levels')
        if to_step == '4':
            return reverse('users:setting-disbursement-checkers')
        if to_step == '5':
            return reverse('users:setting-disbursement-formats')

        return reverse('users:setting-disbursement-makers')


class CollectionFormView(CollectionRootRequiredMixin, FormView):
    template_name = 'users/setting-up-collection/collection.html'
    setup = None

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return CollectionDataForm(request=self.request)

    def get_context_data(self, **kwargs):
        """update context data"""
        data = super().get_context_data(**kwargs)
        data['enabled_steps'] = '-'.join(self.get_setup().disbursement_enabled_steps())
        return data

    def post(self, request, *args, **kwargs):
        form = CollectionDataForm(request.POST, request=self.request)
        if form and form.is_valid():
            setup = self.get_setup()
            setup.collection_setup = True
            setup.save()
            form.save()
            return self.form_valid(form)
        return self.form_invalid(form)

    def get_setup(self):
        if self.setup is None:
            self.setup = Setup.objects.get(user__hierarchy=self.request.user.hierarchy)
        return self.setup

    def get_success_url(self):
        to_step = self.request.GET.get('to_step', None)
        if to_step == '3':
            return reverse('users:setting-collection-uploader')

        return reverse('users:setting-collection-formats')


class BaseFormsetView(TemplateView):
    """BaseView for setup Formsets"""
    setup = None

    def get_context_data(self, **kwargs):
        """update context data"""
        data = super().get_context_data(**kwargs)
        form = kwargs.get('form', None)
        data['form'] = form or self.form_class(
            queryset=self.get_queryset(),
            prefix=self.prefix,
            form_kwargs={'request': self.request}
        )
        data['enabled_steps'] = '-'.join(getattr(self.get_setup(), f'{self.data_type}_enabled_steps')())
        return data

    def post(self, request, *args, **kwargs):
        form = self.form_class(
            request.POST,
            prefix=self.prefix,
            form_kwargs={'request': self.request}
        )
        if form.is_valid():
            return self.form_valid(form)

        return self.render_to_response(self.get_context_data(form=form))

    def get_setup(self):
        if self.setup is None:
            self.setup = Setup.objects.get(user__hierarchy=self.request.user.hierarchy)
        return self.setup

    def form_valid(self, form):
        form.save()
        setup = self.get_setup()
        setattr(setup, f'{self.setup_key}_setup', True)
        setup.save()
        return redirect(self.get_success_url())


class UploaderFormView(CollectionRootRequiredMixin, BaseFormsetView):
    template_name = 'users/setting-up-collection/uploader.html'
    form_class = UploaderMemberFormSet
    model = UploaderUser
    prefix = 'uploader'
    setup_key = 'uploaders'
    data_type = 'collection'

    def get(self, request, *args, **kwargs):
        """Handle GET requests"""
        setup = self.get_setup()
        if not setup.format_collection_setup:
            return redirect('users:setting-collection-formats')
        return self.render_to_response(self.get_context_data())

    def get_success_url(self):
        to_step = self.request.GET.get('to_step', None)
        if to_step == '1':
            return reverse('users:setting-collection-collectiondata')
        if to_step == '2':
            return reverse('users:setting-collection-formats')

        return reverse('data:collection_home')

    def get_queryset(self):
        return self.model.objects.filter(hierarchy=self.request.user.hierarchy)


class FormatFormView(CollectionRootRequiredMixin, BaseFormsetView):
    template_name = 'users/setting-up-collection/formats.html'
    form_class = FormatFormSet
    model = Format
    prefix = 'format'
    setup_key = 'format_collection'
    data_type = 'collection'

    def get(self, request, *args, **kwargs):
        """Handle GET requests"""
        setup = self.get_setup()
        if not setup.collection_setup:
            return reverse('users:setting-collection-collectiondata')
        return self.render_to_response(self.get_context_data())

    def get_success_url(self):
        to_step = self.request.GET.get('to_step', None)
        if to_step == '1':
            return reverse('users:setting-collection-collectiondata')

        return reverse('users:setting-collection-uploader')

    def get_queryset(self):
        return self.model.objects.filter(hierarchy=self.request.user.hierarchy)


class MakerFormView(DisbursementRootRequiredMixin, BaseFormsetView):
    template_name = 'users/setting-up-disbursement/makers.html'
    form_class = MakerMemberFormSet
    model = MakerUser
    prefix = 'maker'
    setup_key = 'maker'
    data_type = 'disbursement'

    def get(self, request, *args, **kwargs):
        """Handle GET requests"""
        setup = self.get_setup()
        if not setup.pin_setup:
            return reverse('users:setting-disbursement-pin')
        return self.render_to_response(self.get_context_data())

    def get_success_url(self):
        to_step = self.request.GET.get('to_step', None)
        if to_step == '1':
            return reverse('users:setting-disbursement-pin')
        if to_step == '4':
            return reverse('users:setting-disbursement-checkers')
        if to_step == '5':
            return reverse('users:setting-disbursement-formats')

        return reverse('users:setting-disbursement-levels')

    def get_queryset(self):
        return self.model.objects.filter(hierarchy=self.request.user.hierarchy)


class CheckerFormView(DisbursementRootRequiredMixin, BaseFormsetView):
    template_name = 'users/setting-up-disbursement/checkers.html'
    form_class = CheckerMemberFormSet
    model = CheckerUser
    prefix = 'checker'
    setup_key = 'checker'
    data_type = 'disbursement'

    def get(self, request, *args, **kwargs):
        """Handle GET requests"""
        setup = self.get_setup()
        if not setup.levels_setup:
            return reverse('users:setting-disbursement-levels')
        return self.render_to_response(self.get_context_data())

    def get_success_url(self):
        to_step = self.request.GET.get('to_step', None)
        if to_step == '1':
            return reverse('users:setting-disbursement-pin')
        if to_step == '2':
            return reverse('users:setting-disbursement-makers')
        if to_step == '3':
            return reverse('users:setting-disbursement-levels')

        return reverse('users:setting-disbursement-formats')

    def get_queryset(self):
        return self.model.objects.filter(hierarchy=self.request.user.hierarchy)


class LevelsFormView(DisbursementRootRequiredMixin, BaseFormsetView):
    template_name = 'users/setting-up-disbursement/levels.html'
    form_class = LevelFormSet
    model = Levels
    prefix = 'level'
    data_type = 'disbursement'

    def get(self, request, *args, **kwargs):
        """Handle GET requests"""

        setup = self.get_setup()
        if not setup.maker_setup:
            return reverse('users:setting-disbursement-makers')
        return self.render_to_response(self.get_context_data())

    def get_success_url(self):
        to_step = self.request.GET.get('to_step', None)
        if to_step == '1':
            return reverse('users:setting-disbursement-pin')
        if to_step == '2':
            return reverse('users:setting-disbursement-makers')
        if to_step == '5':
            return reverse('users:setting-disbursement-formats')

        return reverse('users:setting-disbursement-checkers')

    def get_queryset(self):
        return self.model.objects.filter(created__hierarchy=self.request.user.hierarchy)

    def form_valid(self, form):
        form.save()
        Levels.update_levels_authority(self.request.user.root)
        setup = self.get_setup()
        setup.levels_setup = True
        setup.save()
        return redirect(self.get_success_url())


class CategoryFormView(DisbursementRootRequiredMixin, BaseFormsetView):
    template_name = 'users/setting-up-disbursement/category.html'
    form_class = FileCategoryFormSet
    model = FileCategory
    prefix = 'category'
    setup_key = 'category'
    data_type = 'disbursement'

    def get(self, request, *args, **kwargs):
        """Handle GET requests"""
        setup = self.get_setup()
        if not setup.checker_setup:
            return reverse('users:setting-disbursement-checkers')
        return self.render_to_response(self.get_context_data())

    def get_success_url(self):
        to_step = self.request.GET.get('to_step', None)
        if to_step == '1':
            return reverse('users:setting-disbursement-pin')
        if to_step == '2':
            return reverse('users:setting-disbursement-makers')
        if to_step == '3':
            return reverse('users:setting-disbursement-levels')
        if to_step == '4':
            return reverse('users:setting-disbursement-checkers')

        return reverse('data:disbursement_home')

    def get_queryset(self):
        return self.model.objects.filter(user_created__hierarchy=self.request.user.hierarchy)


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
            qs = qs.filter(hierarchy=self.request.user.hierarchy, user_type__in=[1, 2, 5])
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


class Clients(SuperRequiredMixin, ListView):
    """
    List clients related to same super user.
    Search clients by username, firstname or lastname by "search" query parameter.
    Filter clients by type 'active' or 'inactive' by "q" query parameter.
    """
    model = Client
    paginate_by = 20
    context_object_name = 'users'
    template_name = 'users/clients.html'

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(creator=self.request.user)
        if self.request.GET.get("search"):
            search = self.request.GET.get("search")
            return qs.filter(Q(client__username__icontains=search) |
                             Q(client__first_name__icontains=search) |
                             Q(client__last_name__icontains=search))
        if self.request.GET.get("q"):
            type_of = self.request.GET.get("q")
            if type_of == 'active':
                value = True
            elif type_of == 'inactive':
                value = False
            else:
                return qs
            return qs.filter(is_active=value)
        return qs


class InstantTransactionsView(InstantReviewerRequiredMixin, ListView):
    """
    View for displaying instant transactions
    """
    model = InstantTransaction
    context_object_name = 'transactions'
    paginate_by = 13
    template_name = 'users/instant_viewer.html'
    queryset = InstantTransaction.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset().filter(from_user__hierarchy=self.request.user.hierarchy)

        if self.request.GET.get('search'):                      # Handle search keywords if any
            search_keys = self.request.GET.get('search')
            queryset.filter(
                    Q(uid__iexact=search_keys)|
                    Q(anon_recipient__iexact=search_keys)|
                    Q(failure_reason__icontains=search_keys)
            )

        return queryset


class LevelsView(LevelsFormView):
    """ View for adding levels """
    template_name = 'users/add_levels.html'

    def get(self, request, *args, **kwargs):
        """Handle GET requests"""
        return self.render_to_response(self.get_context_data())

    def get_success_url(self):
        return reverse('users:levels')

    def get_context_data(self, **kwargs):
        """update context data"""
        data = super().get_context_data(**kwargs)
        form = kwargs.get('form', None)
        data['levelform'] = form or self.form_class(
            queryset=self.get_queryset(),
            prefix=self.prefix,
            form_kwargs={'request': self.request}
        )
        return data

    def form_valid(self, form):
        form.save()
        Levels.update_levels_authority(self.request.user.root)
        return redirect(self.get_success_url())


class BaseAddMemberView(DisbursementRootRequiredMixin, CreateView):
    """
    Base View for creating maker and checker
    """
    template_name = 'users/add_member.html'

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.hierarchy = self.request.user.hierarchy
        self.object.save()
        self.object.user_permissions.add(*Permission.objects.filter(user=self.request.user))
        return super().form_valid(form)


class AddCheckerView(BaseAddMemberView):
    """
    View for creating checker
    """
    model = CheckerUser
    form_class = CheckerCreationForm

    def get_form_kwargs(self):
        """
        pass request to form kwargs
        """
        kwargs = super().get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'who': _('checker'), 'success_url': reverse_lazy("users:add_checker")})
        return context


class AddMakerView(BaseAddMemberView):
    """
    View for creating maker
    """
    model = MakerUser
    form_class = MakerCreationForm

    def get_form_kwargs(self):
        """
        pass request to form kwargs
        """
        kwargs = super().get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'who': _('maker'), 'success_url': reverse_lazy("users:add_maker")})
        return context


class ProfileView(DetailView):
    """
    User profile details view.
    """
    model = User
    template_name = 'users/profile.html'

    def get_object(self, queryset=None):
        return get_object_or_404(User, username=self.kwargs['username'])


class ProfileUpdateView(UpdateView):
    """
    User profile update view.
    """
    model = User
    template_name = 'users/profile_update.html'
    form_class = ProfileEditForm

    def get_object(self, queryset=None):
        return get_object_or_404(User, username=self.kwargs['username'])


class SuperAdminRootSetup(SuperRequiredMixin, CreateView):
    """
    View for SuperAdmin for creating root user.
    """
    model = RootUser
    form_class = RootCreationForm
    template_name = 'entity/add_root.html'

    def get_success_url(self, is_collection=False):
        if is_collection:
            return reverse('users:clients')

        token, created = ExpiringToken.objects.get_or_create(user=self.object)
        if created:
            return reverse('disbursement:add_agents', kwargs={'token': token.key})
        if token.expired():
            token.delete()
            token = ExpiringToken.objects.create(user=self.object)
        return reverse('disbursement:add_agents', kwargs={'token': token.key})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs

    def form_valid(self, form):
        self.object = form.save()
        entity_dict = {
            "user": self.request.user,
            "entity": self.object
        }
        is_collection = self.object.data_type() == 2
        if is_collection:
            entity_dict['agents_setup'] = True

        EntitySetup.objects.create(**entity_dict)
        Client.objects.create(creator=self.request.user, client=self.object)
        ROOT_CREATE_LOGGER.debug(f"""[NEW ADMIN CREATED]
        User: {self.request.user.username}
        Created new Root/Admin with username: {self.object.username} from IP Address {get_client_ip(self.request)}""")

        return HttpResponseRedirect(self.get_success_url(is_collection))


class SuperAdminCancelsRootSetupView(SuperOwnsClientRequiredMixin, View):
    """
    View for canceling Root setups by deleting created entity setups.
    """

    def post(self, request, *args, **kwargs):
        """Handles POST requests to this View"""
        username = self.kwargs.get('username')

        try:
            User.objects.get(username=username).delete()
            DELETE_USER_VIEW_LOGGER.debug(f"[USER DELETED]\n"
                f"User: {request.user.username}, Deleted user with username: {username}")
            return redirect(reverse("data:disbursement_home"))
        except User.DoesNotExist:
            DELETE_USER_VIEW_LOGGER.debug(f"[USER DOES NOT EXIST]\n"
                f"User: {request.user.username}, tried to delete user with username {username} which does not exist")
            return redirect(reverse("data:disbursement_home"))


class ClientFeesSetup(SuperRequiredMixin, SuperFinishedSetupMixin, CreateView):
    """
    View for SuperAdmin to setup fees for the client
    """
    model = Client
    form_class = ClientFeesForm
    template_name = 'entity/add_client_fees.html'
    success_url = reverse_lazy('users:clients')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        root = ExpiringToken.objects.get(key=self.kwargs['token']).user
        kwargs.update({'instance': root.client})
        return kwargs


class CustomClientFeesProfilesUpdateView(SuperOwnsCustomizedBudgetClientRequiredMixin, UpdateView):
    """
    View for updating client's fees profile
    """

    model = Client
    form_class = CustomClientProfilesForm
    template_name = 'entity/update_fees.html'

    def get_object(self, queryset=None):
        return get_object_or_404(Client, creator=self.request.user, client__username=self.kwargs.get('username'))


class EntityBranding(SuperRequiredMixin, UpdateView):
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


class PasswordResetView(AbstractPasswordResetView):
    success_url = reverse_lazy('users:password_reset_done')


class OTPLoginView(FormView):
    template_name = 'two_factor/login.html'
    success_url = '/'

    def post(self, request, *args, **kwargs):
        form = OTPTokenForm(data=request.POST, user=self.request.user)
        if form.is_valid():
            request.user.is_totp_verified = True
            request.user.save()
            return self.form_valid(form)
        return self.form_invalid(form)

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return OTPTokenForm(user=self.request.user)


class ForgotPasswordView(FormView):
    form_class = ForgotPasswordForm
    template_name = 'users/forget-password.html'

    def form_valid(self, form):
        """called when form is valid"""
        form.send_email()
        context = self.get_context_data()
        context['success'] = True
        context['form'] = self.form_class()
        # no success url redirect
        return render(self.request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests: instantiate a form instance with the passed
        POST variables and then check if it's valid.
        """
        form = self.form_class(request.POST)
        if form.is_valid():
            return self.form_valid(form)

        return self.form_invalid(form)


class RedirectPageView(View):
    template_name = 'users/redirect_page.html'

    def get(self, request, *args, **kwargs):
        if not (request.user.is_upmaker or (request.user.is_root and request.user.data_type() == 3)):
            return redirect('/')
        status = request.GET.get('status', None)
        if status is not None and status in ['disbursement', 'collection']:
            request.session['status'] = status
            return redirect(reverse(f'data:{status}_home'))

        return render(request, self.template_name, {})


class ExpiringAuthToken(ObtainExpiringAuthToken):

    def post(self, request):
        """Respond to POSTed username/password with token."""
        serializer = AuthTokenSerializer(data=request.data, context={"request": request})

        if serializer.is_valid():
            token, _ = self.model.objects.get_or_create(user=serializer.validated_data['user'])

            if token.expired():
                # If the token is expired, generate a new one.
                token.delete()
                token = self.model.objects.create(user=serializer.validated_data['user'])

            data = {'token': token.key}
            return Response(data)

        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


def login_view(request):
    """
    Function that allows users to login.
    Checkers must do two factor authentication every login but makers don't.
    Non active users can't login.
    """
    user = None

    if request.user.is_authenticated:
        if request.user.is_checker:
            return HttpResponseRedirect(reverse('two_factor:profile'))
        return redirect('data:main_view')
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request=request, username=username, password=password)
        if user and not user.is_instantapichecker:
            if user.is_active:
                login(request, user)
                LOGIN_LOGGER.debug(f"User: {request.user.username} Logged In from IP Address {get_client_ip(request)}")
                if user.is_checker:
                    user.is_totp_verified = False
                    user.save()
                    return HttpResponseRedirect(reverse('two_factor:profile'))

                if user.is_upmaker or (user.is_root and user.data_type() == 3):
                    return HttpResponseRedirect(reverse('users:redirect'))

                if user.is_instantapiviewer:
                    return HttpResponseRedirect(reverse('users:instant_transactions'))

                return HttpResponseRedirect(reverse('data:main_view'))
            else:
                FAILED_LOGIN_LOGGER.debug(f"""[FAILED LOGIN]
                Failed Attempt from non active user with username: {username} and IP Addr {get_client_ip(request)}""")
                return HttpResponse("Your account has been disabled")
        elif user is not None and user.is_instantapichecker:
            FAILED_LOGIN_LOGGER.debug(f"""[API USER LOGIN ATTEMPT]
            Failed Attempt from instant API user with username: {username} and IP Addr {get_client_ip(request)}""")
            return render(request, 'data/login.html', {'error_invalid': "You're not permitted to login."})
        else:
            # Bad login details were provided. So we can't log the user in.
            FAILED_LOGIN_LOGGER.debug(f"""[FAILED LOGIN]
            Failed Login Attempt from user with username: {username} and IP Address {get_client_ip(request)}""")
            return render(request, 'data/login.html', {'error_invalid': 'Invalid login details supplied.'})
    else:
        return render(request, 'data/login.html')


def ourlogout(request):
    """
    Function that allows users to logout.
    Remove otp verification from user.
    """
    if isinstance(request.user, AnonymousUser):
        return HttpResponseRedirect(reverse('users:user_login_view'))
    LOGOUT_LOGGER.debug(f"User: {request.user.username} Logged Out from IP Address {get_client_ip(request)}")
    request.user.is_totp_verified = False
    request.user.save()
    logout(request)
    response = HttpResponseRedirect(reverse('users:user_login_view'))
    return response


@login_required
def change_password(request, user):
    """
    View for changing or creating password.
    If user already has password then he must enter old one.
    Else enter new password.
    """
    context = {}
    if request.method == 'GET':
        if request.user.has_usable_password():
            form = PasswordChangeForm(request)
        else:
            form = SetPasswordForm(request)
        context['form'] = form
        return render(request, 'data/change_password.html', context=context)

    if request.user.has_usable_password():
        form = PasswordChangeForm(request.user, request.POST)
    else:
        form = SetPasswordForm(request.user, request.POST)

    if not form.is_valid():
        context['form'] = form
        return render(request, 'data/change_password.html', context=context)

    form.save()
    return HttpResponseRedirect(reverse('users:user_login_view'))


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
            else:
                user = User.objects.get(id=int(data['user_id']))
                user.delete()
            DELETE_USER_VIEW_LOGGER.debug(f"""[USER DELETED]
            User: {request.user.username}
            Deleted user with username: {user.username}""")
            return HttpResponse(content=json.dumps({"valid": "true"}), content_type="application/json")
        except User.DoesNotExist:
            DELETE_USER_VIEW_LOGGER.debug(f"""[USER DOES NOT EXIST]
            User with id {data['user_id']} doesn't exist to be deleted""")
            return HttpResponse(content=json.dumps({"valid": "false"}), content_type="application/json")
    else:
        raise Http404()


@login_required
def toggle_client(request):
    """
    Activate or deactivate client
    """
    if request.is_ajax() and request.method == 'POST' and request.user.is_superadmin:
        data = request.POST.copy()
        is_toggled = Client.objects.toggle(id=int(data['user_id']))
        return HttpResponse(content=json.dumps({"valid": is_toggled}), content_type="application/json")
    else:
        raise Http404()
