from __future__ import print_function, unicode_literals

import datetime
import json
import logging

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.views import PasswordResetView as AbstractPasswordResetView
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.views.generic.edit import FormView
from django_otp.forms import OTPTokenForm
from rest_framework_expiring_authtoken.models import ExpiringToken

from data.forms import FileCategoryForm
from data.utils import get_client_ip
from users.forms import (CheckerMemberFormSet,
                         BrandForm, LevelFormSet, MakerMemberFormSet, PasswordChangeForm,
                         SetPasswordForm, CheckerCreationForm, MakerCreationForm,
                         ProfileEditForm, RootCreationForm, OTPTokenForm)
from users.mixins import RootRequiredMixin, SuperRequiredMixin
from users.models import CheckerUser, Levels, MakerUser, Setup, User, Brand
from users.models import Client
from users.models import EntitySetup
from users.models import RootUser

LOGIN_LOGGER = logging.getLogger("login")
LOGOUT_LOGGER = logging.getLogger("logout")
FAILED_LOGIN_LOGGER = logging.getLogger("login_failed")
SETUP_VIEW_LOGGER = logging.getLogger("setup_view")
DELETE_USER_VIEW_LOGGER = logging.getLogger("delete_user_view")
LEVELS_VIEW_LOGGER = logging.getLogger("levels_view")
ROOT_CREATE_LOGGER = logging.getLogger("root_create")

def ourlogout(request):
    """
    Function that allows users to logout.
    Remove otp verification from user. 
    """
    if isinstance(request.user, AnonymousUser):
        return HttpResponseRedirect(reverse('users:user_login_view'))
    now = datetime.datetime.now()
    LOGOUT_LOGGER.debug(
        '%s logged out at %s from IP Address %s' % (
            request.user.username, now, get_client_ip(request)))
    request.user.is_totp_verified = False
    request.user.save()
    logout(request)
    response = HttpResponseRedirect(reverse('users:user_login_view'))
    return response


def login_view(request):
    """
    Function that allows users to login.
    Checkers must do two factor authentication every login but makers don't.
    Non active users can't login.
    """
    if request.user.is_authenticated:
        if request.user.is_checker:
            return HttpResponseRedirect(reverse('two_factor:profile'))
        return redirect('data:main_view')
    now = datetime.datetime.now()
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        if user:
            if user.is_active:
                login(request, user)
                IP = get_client_ip(request)
                LOGIN_LOGGER.debug(
                    'Logged in ' + str(now) + ' %s with IP Address: %s' % (
                        request.user, IP))
                if user.is_checker:
                    user.is_totp_verified = False
                    user.save()
                    return HttpResponseRedirect(reverse('two_factor:profile'))

                return HttpResponseRedirect(reverse('data:main_view'))
            else:
                FAILED_LOGIN_LOGGER.debug(
                    f"Failed Login Attempt from non active user with username {username} and IP Address {get_client_ip(request)}")
                return HttpResponse("Your account has been disabled")
        else:
            # Bad login details were provided. So we can't log the user in.
            FAILED_LOGIN_LOGGER.debug(
                'Failed Login Attempt %s at %s from IP Address %s' % (
                    username, str(now), get_client_ip(request)))
            return render(request, 'data/login.html', {'error_invalid': 'Invalid login details supplied.'})
    else:
        return render(request, 'data/login.html')


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


class SettingsUpView(RootRequiredMixin, CreateView):
    """
    View for the root user to setup levels, makers, checkers and file category.

    """
    model = MakerUser
    template_name = 'users/settings-up.html'
    form_class = MakerMemberFormSet
    success_url = "/"

    def post(self, request, *args, **kwargs):
        if request.is_ajax():
            form = None
            data = request.POST.copy()
            FileCategoryForm.request = request
            # populate forms with data
            if data['step'] == '1':
                form = LevelFormSet(
                    data,
                    prefix='level'
                )
            elif data['step'] == '3':
                form = CheckerMemberFormSet(
                    data,
                    prefix='checker',
                    # pass request to get hierarchy levels and include them in checker form
                    form_kwargs={'request': self.request}
                )
            elif data['step'] == '2':
                form = MakerMemberFormSet(
                    data,
                    prefix='maker'
                )
            elif data['step'] == '4':
                file_category = getattr(self.request.user, 'file_category', None)
                # user already has a file_category then update
                if file_category is not None:
                    form = FileCategoryForm(
                        instance=file_category, data=request.POST)
                # create new file_category
                else:    
                    form = FileCategoryForm(data=request.POST)
            
            if form and form.is_valid():              
                objs = form.save(commit=False)
                
                # if form is a formset
                if not isinstance(form, FileCategoryForm):
                    # delete formsets marked to be deleted
                    for obj in form.deleted_objects:
                        obj.delete()
              
                    for obj in objs:
                        obj.hierarchy = request.user.hierarchy
                        obj.created_id = request.user.root.id
                        obj.save()
                        obj.permissions.add(request.user.root.get_all_permissions())
                     
                #if form is filecategory form
                else:
                    objs.user_created = request.user.root
                    objs.save()
                # update setup model flags
                if data['step'] == '1':
                    setup = Setup.objects.get(
                        user__hierarchy=request.user.hierarchy)
                    setup.levels_setup = True
                    setup.save()
                elif data['step'] == '3':
                    setup = Setup.objects.get(
                        user__hierarchy=request.user.hierarchy)
                    setup.users_setup = True
                    setup.save()
                if data['step'] == '4':
                    setup = Setup.objects.get(
                        user__hierarchy=request.user.hierarchy)
                    setup.category_setup = True
                    setup.save()
                    SETUP_VIEW_LOGGER.debug(
                        f'Root user: {request.user.username} Finished Setup successfully')
                    return HttpResponseRedirect(reverse("data:main_view"), status=278)
                return HttpResponse(content=json.dumps({"valid": True}), content_type="application/json")

            #form could be filecategory or formset 
            #only formsets have non_form_errors but normal form doesn't
            non_form_errors = getattr(form, 'non_form_errors', None)
            if non_form_errors is not None:
                non_form_errors = non_form_errors()
            return HttpResponse(
                content=json.dumps({
                    "valid": False,                                                    
                    "reason": "validation", 
                    "errors": form.errors, 
                    "non_form_errors": non_form_errors
                }),
                content_type="application/json")

        SETUP_VIEW_LOGGER.debug(
            f'404 Response because The POST Request is not ajax from user {request.user.username}')
        raise Http404()

    def get_context_data(self, **kwargs):
        """
        Add the needed forms to the context.
        Add step number to context because pressing previous refresh the view but
        with the step as query paramter to know wich step to initiate when loading the template.
        """
        data = super().get_context_data(**kwargs)

        data['makerform'] = self.form_class(
            queryset=self.model.objects.filter(
                hierarchy=self.request.user.hierarchy
            ),
            prefix='maker'
        )
        data['checkerform'] = CheckerMemberFormSet(
            queryset=CheckerUser.objects.filter(
                hierarchy=self.request.user.hierarchy
            ),
            prefix='checker',
            form_kwargs={'request': self.request}
        )
        data['levelform'] = LevelFormSet(
            queryset=Levels.objects.filter(
                created__hierarchy=self.request.user.hierarchy
            ),
            prefix='level'
        )
        data['step'] = self.request.GET.get('step', '0')
        if int(data['step']) < 0 or int(data['step']) > 2:
            data['step'] = '0'
        file_category = getattr(self.request.user, 'file_category', None)
        if file_category is not None:
            data['filecategoryform'] = FileCategoryForm(instance=file_category)
        else:
            data['filecategoryform'] = FileCategoryForm()

        return data

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = self.get_form_class()
        kwargs = self.get_form_kwargs()
        kwargs.pop('instance')
        return form_class(**kwargs)


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
        qs = super().get_queryset()
        qs = qs.filter(hierarchy=self.request.user.hierarchy,
                       user_type__in=[1, 2])
        if self.request.GET.get("search"):
            search = self.request.GET.get("search")
            return qs.filter(Q(username__icontains=search) |
                             Q(first_name__icontains=search) |
                             Q(last_name__icontains=search)
                             )
        if self.request.GET.get("q"):
            type_of = self.request.GET.get("q")
            if type_of == 'maker':
                value = 1
            elif type_of == 'checker':
                value = 2
            else:
                return qs
            return qs.filter(user_type=value)
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
                             Q(client__last_name__icontains=search)
                             )
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


def toggle_client(request):
    """
    Activate or deactivate client
    """
    if request.is_ajax() and request.method=='POST':
        data = request.POST.copy()
        is_toggled = Client.objects.toggle(id=int(data['user_id']))
        return HttpResponse(content=json.dumps({"valid": is_toggled}), content_type="application/json")
    else:
        raise Http404()

@login_required
def delete(request):
    """
    Delete any user by user_id
    """
    if request.is_ajax() and request.method == 'POST':
        try:
            data = request.POST.copy()
            user = User.objects.get(id=int(data['user_id']))
            user.delete()
            DELETE_USER_VIEW_LOGGER.debug(f'user deleted with username {user.username}')
            return HttpResponse(content=json.dumps({"valid": "true"}), content_type="application/json")
        except User.DoesNotExist:
            DELETE_USER_VIEW_LOGGER.debug(
                f"user with id {data['user_id']} doesn't exist to be deleted")
            return HttpResponse(content=json.dumps({"valid": "false"}), content_type="application/json")
    else:
        raise Http404()


class LevelsView(RootRequiredMixin, View):
    """
    View for adding Levels
    """

    def post(self, request, *args, **kwargs):

        form = LevelFormSet(
            request.POST,
            prefix='level'
        )
        if form and form.is_valid():

            objs = form.save(commit=False)
            
            for obj in form.deleted_objects:
                obj.delete()
            
            for obj in objs:
                obj.hierarchy = request.user.hierarchy
                obj.created_id = request.user.root.id
                obj.save()
                
            return HttpResponse(content=json.dumps({"valid": True}), content_type="application/json")

        return HttpResponse(content=json.dumps({
            "valid": False,
            "reason": "validation",
            "errors": form.errors,
            "non_form_errors": form.non_form_errors()
        }), content_type="application/json")

    def get(self, request, *args, **kwargs):
        initial_query = Levels.objects.filter(
            created__hierarchy=request.user.hierarchy
        )
        context = {
            'levelform': LevelFormSet(queryset=initial_query, prefix='level')
        }
        return render(request, 'users/add_levels.html', context)


class BaseAddMemberView(RootRequiredMixin, CreateView):
    """
    Base View for creating maker and checker
    """
    template_name = 'users/add_member.html'

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.hierarchy = self.request.user.hierarchy
        self.object.save()
        self.object.permissions.add(self.request.user.get_all_permissions())
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
        context.update(
            {'who': _('checker'), 'success_url': reverse_lazy("users:add_checker")})
        return context


class AddMakerView(BaseAddMemberView):
    """
    View for creating maker
    """
    model = MakerUser
    form_class = MakerCreationForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {'who': _('maker'), 'success_url': reverse_lazy("users:add_maker")})
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
    View for super admin for creating root user.
    """
    model = RootUser
    form_class = RootCreationForm
    template_name = 'entity/add_root.html'

    def get_success_url(self):
        token, created = ExpiringToken.objects.get_or_create(user=self.object)
        if created:
            return reverse('disbursement:add_agents', kwargs={'token': token.key})
        if token.expired():
            token = ExpiringToken.objects.create(user=self.object)
        return reverse('disbursement:add_agents', kwargs={'token': token.key})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs

    def form_valid(self, form):
        self.object = form.save()
        EntitySetup.objects.create(user=self.request.user, entity=self.object)
        Client.objects.create(creator=self.request.user, client=self.object)
        ROOT_CREATE_LOGGER.debug(
            f'Root created with username {self.object.username} from IP Address {get_client_ip(self.request)}')
        return HttpResponseRedirect(self.get_success_url())


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

    def post(self,request,*args,**kwargs):
        form = OTPTokenForm(data=request.POST, user=self.request.user)
        if form.is_valid():
            request.user.is_totp_verified = True
            request.user.save()
            return self.form_valid(form)
        return self.form_invalid(form)   

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        
        return OTPTokenForm(user=self.request.user)
