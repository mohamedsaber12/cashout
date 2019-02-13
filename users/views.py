from __future__ import print_function, unicode_literals

import datetime
import json
import logging

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser,Permission
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
from django.forms.formsets import BaseFormSet
from rest_framework_expiring_authtoken.models import ExpiringToken

from data.forms import FileCategoryForm, CollectionDataForm,FormatFormSet
from data.utils import get_client_ip
from data.models import Format
from users.forms import (CheckerMemberFormSet,
                         BrandForm, LevelFormSet, MakerMemberFormSet, PasswordChangeForm,
                         SetPasswordForm, CheckerCreationForm, MakerCreationForm,
                         ProfileEditForm, RootCreationForm, OTPTokenForm, ForgotPasswordForm,
                         UploaderMemberFormSet)
from users.mixins import RootRequiredMixin, SuperRequiredMixin
from users.models import (CheckerUser, Levels, MakerUser, UploaderUser,
                            Setup, User, Brand, Client, EntitySetup, RootUser)
from users.decorators import root_or_superadmin

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

                if user.is_upmaker or (user.is_root and user.data_type() == 3):
                    return HttpResponseRedirect(reverse('users:redirect'))
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


class CollectionSettingsUpView(RootRequiredMixin, CreateView):
    """
    View for the root user to setup levels, makers, checkers and file category.

    """
    model = UploaderUser
    template_name = 'users/settings-up-collection.html'
    form_class = UploaderMemberFormSet
    success_url = "/"

    def post(self, request, *args, **kwargs):        
        if request.is_ajax():
            form = None
            data = request.POST.copy()
            FileCategoryForm.request = request
            # populate forms with data
       
            if data['prefix'] == 'uploader':
                form = UploaderMemberFormSet(
                    data,
                    prefix='uploader'
                )
            elif data['prefix'] == 'format':
                form = FormatFormSet(
                    data,
                    prefix='format',
                    form_kwargs={'request': self.request}
                )
            elif data['prefix'] == 'collection_data':
                form = CollectionDataForm(data=request.POST, request=self.request)
            
            form_is_formset = isinstance(form, BaseFormSet)
            
            if form and form.is_valid():              
                objs = form.save(commit=False)
                
                # if form is a formset
                if form_is_formset:
                    # delete formsets marked to be deleted
                    for obj in form.deleted_objects:
                        obj.delete()

                    if len(objs) > 0:
                        if isinstance(objs[0], User):
                            for obj in objs:
                                obj.hierarchy = request.user.hierarchy
                                obj.save()
                                obj.user_permissions.add(*Permission.objects.filter(user=request.user.root))
                        elif isinstance(objs[0], Format) or isinstance(objs[0], Levels):
                            for obj in objs:
                                obj.save()

                #if form is CollectionData form
                elif isinstance(form, CollectionDataForm):
                    objs.save()
                
         
                if data['prefix'] == 'uploader':
                    setup = Setup.objects.get(
                        user__hierarchy=request.user.hierarchy)
                    setup.uploaders_setup = True
                    setup.save()
                    SETUP_VIEW_LOGGER.debug(
                        f'Root user: {request.user.username} Finished Collection Setup successfully')
                    return HttpResponseRedirect(reverse("data:main_view"), status=278)
                elif data['prefix'] == 'format':
                    setup = Setup.objects.get(
                        user__hierarchy=request.user.hierarchy)
                    setup.format_collection_setup = True
                    setup.save()
                elif data['prefix'] == 'collection_data':
                    setup = Setup.objects.get(
                        user__hierarchy=request.user.hierarchy)
                    setup.collection_setup = True
                    setup.save()


                return HttpResponse(content=json.dumps({"valid": True}), content_type="application/json")

            return HttpResponse(
                content=json.dumps({
                    "valid": False,                                                    
                    "reason": "validation", 
                    "errors": form.errors, 
                    #only formsets have non_form_errors but normal form doesn't
                    "non_form_errors": form.non_form_errors() if form_is_formset else None,
                    "form_is_formset": form_is_formset,
                    'prefix': data['prefix']
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
        data['uploaderform'] = UploaderMemberFormSet(
            queryset=UploaderUser.objects.filter(
                hierarchy=self.request.user.hierarchy
            ),
            prefix='uploader'
        )

        data['collectiondataform'] = CollectionDataForm(request=self.request)

        data['formatform'] = FormatFormSet(
            queryset=Format.objects.filter(
                hierarchy=self.request.user.hierarchy,
                data_type = 2
            ),
            prefix='format',
            form_kwargs={'request': self.request}
        )   

        data['step'] = self.request.GET.get('step', '0')

        if  (int(data['step']) <= 0 or int(data['step']) > 2):
            data['step'] = '0'
            return data
        
        setup = Setup.objects.get(user__hierarchy=self.request.user.hierarchy)
        prefix = self.request.GET.get('prefix', None)
        
        if (
            (
                prefix is None or
                prefix not in ['collection_data', 'format', 'uploader']
            ) or
            (prefix == 'format' and not setup.collection_setup) or
            (prefix == 'uploader')
        ):
            data['step'] = '0'
        
        return data

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = self.get_form_class()
        kwargs = self.get_form_kwargs()
        kwargs.pop('instance')
        return form_class(**kwargs)


class DisbursementSettingsUpView(RootRequiredMixin, CreateView):
    """
    View for the root user to setup levels, makers, checkers and file category.

    """
    model = MakerUser
    template_name = 'users/settings-up-disbursement.html'
    form_class = MakerMemberFormSet
    success_url = "/"

    def post(self, request, *args, **kwargs):
        if request.is_ajax():
            form = None
            data = request.POST.copy()
            FileCategoryForm.request = request
            # populate forms with data
            if data['prefix'] == 'level':
                form = LevelFormSet(
                    data,
                    prefix='level',
                    form_kwargs={'request': self.request}
                )

            elif data['prefix'] == 'checker':
                form = CheckerMemberFormSet(
                    data,
                    prefix='checker',
                    # pass request to get hierarchy levels and include them in checker form
                    form_kwargs={'request': self.request}
                )
            elif data['prefix'] == 'maker':
                form = MakerMemberFormSet(
                    data,
                    prefix='maker'
                )
            elif data['prefix'] == 'category':
                file_category = getattr(
                    self.request.user, 'file_category', None)
                # user already has a file_category then update
                if file_category is not None:
                    form = FileCategoryForm(
                        instance=file_category, data=request.POST)
                # create new file_category
                else:
                    form = FileCategoryForm(data=request.POST)

            elif data['prefix'] == 'format':
                form = FormatFormSet(
                    data,
                    prefix='format',
                    form_kwargs={'request': self.request}
                )
           
            form_is_formset = isinstance(form, BaseFormSet)

            if form and form.is_valid():
                objs = form.save(commit=False)

                # if form is a formset
                if form_is_formset:
                    # delete formsets marked to be deleted
                    for obj in form.deleted_objects:
                        obj.delete()

                    if len(objs) > 0:
                        if isinstance(objs[0], User):
                            for obj in objs:
                                obj.hierarchy = request.user.hierarchy
                                obj.save()
                                obj.user_permissions.add(
                                    *Permission.objects.filter(user=request.user.root))
                        elif isinstance(objs[0], Format) or isinstance(objs[0], Levels):
                            for obj in objs:
                                obj.save()

                #if form is filecategory form
                elif isinstance(form, FileCategoryForm):
                    objs.user_created = request.user.root
                    objs.save()

                # update setup model flags
                if data['prefix'] == 'level':
                    setup = Setup.objects.get(
                        user__hierarchy=request.user.hierarchy)
                    setup.levels_setup = True
                    setup.save()
                elif data['prefix'] == 'checker':
                    setup = Setup.objects.get(
                        user__hierarchy=request.user.hierarchy)
                    setup.users_setup = True
                    setup.save()
                elif data['prefix'] == 'category':
                    setup = Setup.objects.get(
                        user__hierarchy=request.user.hierarchy)
                    setup.category_setup = True
                    setup.save()
                elif data['prefix'] == 'format':
                    setup = Setup.objects.get(
                        user__hierarchy=request.user.hierarchy)
                    setup.format_disbursement_setup = True
                    setup.save()
                    SETUP_VIEW_LOGGER.debug(
                        f'Root user: {request.user.username} Finished Disbursement Setup successfully')
                    return HttpResponseRedirect(reverse("data:main_view"), status=278)
              
                return HttpResponse(content=json.dumps({"valid": True}), content_type="application/json")

            return HttpResponse(
                content=json.dumps({
                    "valid": False,
                    "reason": "validation",
                    "errors": form.errors,
                    #only formsets have non_form_errors but normal form doesn't
                    "non_form_errors": form.non_form_errors() if form_is_formset else None,
                    "form_is_formset": form_is_formset,
                    'prefix': data['prefix']
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
        category = getattr(self.request.user, 'file_category', None)
        if category is not None:
            data['filecategoryform'] = FileCategoryForm(instance=category)
        else:
            data['filecategoryform'] = FileCategoryForm()

        data['makerform'] = self.form_class(
            queryset=MakerUser.objects.filter(
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
            prefix='level',
            form_kwargs={'request': self.request}
        )

        data['formatform'] = FormatFormSet(
            queryset=Format.objects.filter(
                hierarchy=self.request.user.hierarchy,
                data_type=1
            ),
            prefix='format',
            form_kwargs={'request': self.request}
        )

        data['step'] = self.request.GET.get('step', '0')
        if data['step'] == 0:
            return data
        if (int(data['step']) < 0 or int(data['step']) > 4):
            data['step'] = '0'
            return data

        setup = Setup.objects.get(user__hierarchy=self.request.user.hierarchy)
        prefix = self.request.GET.get('prefix', None)

        if (
            (
                prefix is None or
                prefix not in ['level', 'format',
                                'maker', 'checker', 'category']
            ) or
            (prefix == 'maker' and not setup.levels_setup) or
            (
                prefix == 'checker' and not MakerUser.objects.filter(
                    hierarchy=self.request.user.hierarchy).exists()
            ) or
            (
                prefix == 'category' and not setup.users_setup
            ) or
            (
                prefix == 'format'
            )
        ):
            data['step'] = '0'

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
        if 'disbursement' == self.request.user.get_status(self.request):

            qs = super().get_queryset()
            qs = qs.filter(hierarchy=self.request.user.hierarchy,
                        user_type__in=[1, 2,5])
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
            qs = UploaderUser.objects.filter(
                hierarchy=self.request.user.hierarchy)
        
        if self.request.GET.get("search"):
            search = self.request.GET.get("search")
            return qs.filter(Q(username__icontains=search) |
                             Q(first_name__icontains=search) |
                             Q(last_name__icontains=search)
                             )
        
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


@login_required
def toggle_client(request):
    """
    Activate or deactivate client
    """
    if request.is_ajax() and request.method=='POST' and request.user.is_superadmin:
        data = request.POST.copy()
        is_toggled = Client.objects.toggle(id=int(data['user_id']))
        return HttpResponse(content=json.dumps({"valid": is_toggled}), content_type="application/json")
    else:
        raise Http404()


@root_or_superadmin
@login_required
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
            prefix='level',
            form_kwargs={'request': self.request}
        )
        if form and form.is_valid():

            objs = form.save(commit=False)
            
            for obj in form.deleted_objects:
                obj.delete()
            
            for obj in objs:
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
            'levelform': LevelFormSet(queryset=initial_query, prefix='level', form_kwargs={'request': self.request})
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

    def get_success_url(self, is_collection=False):
        
        if is_collection:
            return reverse('users:clients')

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
        entity_dict = {
            "user": self.request.user,
            "entity": self.object
        }
        is_collection = self.object.data_type() == 2
        if is_collection:
            entity_dict['agents_setup'] = True

        EntitySetup.objects.create(**entity_dict)
        Client.objects.create(creator=self.request.user, client=self.object)
        ROOT_CREATE_LOGGER.debug(
            f'Root created with username {self.object.username} from IP Address {get_client_ip(self.request)}')
        return HttpResponseRedirect(self.get_success_url(is_collection))


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
        else:
            return self.form_invalid(form)


class RedirectPageView(View):
    template_name = 'users/redirect_page.html'

    def get(self, request, *args, **kwargs):
        if not (request.user.is_upmaker or (request.user.is_root and request.user.data_type() == 3)):
            return redirect('/')
        status = request.GET.get('status',None)
        if status is not None and status in ['disbursement','collection']:
            request.session['status'] = status
            return redirect(reverse('data:main_view'))

        return render(request, self.template_name, {})
