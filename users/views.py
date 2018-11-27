from __future__ import print_function, unicode_literals

import datetime
import json
import logging

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from data.forms import FileCategoryForm
from data.models import FileCategory
from data.utils import get_client_ip
from users.forms import (CheckerCreationForm, CheckerMemberFormSet,
                         LevelFormSet, MakerCreationForm, MakerMemberFormSet,
                         PasswordChangeForm, ProfileEditForm, SetPasswordForm)
from users.mixins import RootRequiredMixin
from users.models import CheckerUser, Levels, MakerUser, Setup, User

LOGIN_LOGGER = logging.getLogger("login")
LOGOUT_LOGGER = logging.getLogger("logout")
UPLOAD_LOGGER = logging.getLogger("upload")
FAILED_LOGIN_LOGGER = logging.getLogger("login_failed")


def ourlogout(request):
    """
    Function that allows users to logout
    """
    if isinstance(request.user, AnonymousUser):
        return HttpResponseRedirect(reverse('users:user_login_view'))
    now = datetime.datetime.now()
    LOGOUT_LOGGER.debug(
        '%s logged out at %s from IP Address %s' % (
            request.user.username, now, get_client_ip(request)))
    request.user.is_otp_verified = False
    request.user.save()

    logout(request)
    response = HttpResponseRedirect(reverse('users:user_login_view'))
    response.delete_cookie('otp_checked')
    return response


def login_view(request):
    """
    Function that allows users to login
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
                    return HttpResponseRedirect(reverse('two_factor:profile'))

                return HttpResponseRedirect(reverse('data:main_view'))
            else:
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
    context['form'] = form
    context['MESSAGE'] = "Password changed successfully"
    if context['MESSAGE'] is "Password changed successfully":
        return HttpResponseRedirect(reverse('users:user_login_view'))

    return render(request, 'data/change_password.html', context)


class SettingsUpView(RootRequiredMixin, CreateView):
    model = MakerUser
    template_name = 'users/settings-up.html'
    form_class = MakerMemberFormSet
    success_url = "/"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_superuser:
            if request.user.is_root:
                return super().dispatch(request, *args, **kwargs)
        return self.handle_no_permission()

    def post(self, request, *args, **kwargs):
        if request.is_ajax():
            form = None
            data = request.POST.copy()
            FileCategoryForm.request = request
            if data['step'] == '1':
                initial_query = Levels.objects.filter(
                    created__hierarchy=self.request.user.hierarchy
                )

                form = LevelFormSet(
                    data,
                    prefix='level',
                    queryset=initial_query
                )

            elif data['step'] == '3':
                form = CheckerMemberFormSet(
                    data,
                    prefix='checker',
                    form_kwargs={'request': self.request}
                )
            elif data['step'] == '2':
                form = MakerMemberFormSet(
                    data,
                    prefix='maker'
                )
            elif data['step'] == '4':
                try:
                    form = FileCategoryForm(
                        instance=self.request.user.file_category, data=request.POST)
                except FileCategory.DoesNotExist:
                    form = FileCategoryForm(data=request.POST)
            if form and form.is_valid():

                objs = form.save(commit=False)
                try:
                    for obj in form.deleted_objects:
                        obj.delete()
                except AttributeError:
                    pass
                try:
                    for obj in objs:
                        obj.hierarchy = request.user.hierarchy
                        obj.created_id = request.user.root.id
                        try:
                            obj.save()
                        except IntegrityError as e:
                            print('IntegrityError', e)
                            return HttpResponse(content=json.dumps({"valid": False, "reason": "integrity"}), content_type="application/json")
                except TypeError as e:
                    print('TypeError', e)
                    objs.user_created = request.user.root
                    objs.save()

                payload = {"valid": True, "data": "levels"} if data["step"] == "1" else {
                    "valid": True}
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
                if data['step'] == '4' and payload['valid']:
                    setup = Setup.objects.get(
                        user__hierarchy=request.user.hierarchy)
                    setup.category_setup = True
                    setup.save()
                    return HttpResponseRedirect(reverse("data:main_view"), status=278)
                return HttpResponse(content=json.dumps(payload), content_type="application/json")

            non_form_errors = getattr(form, 'non_form_errors', None)
            if non_form_errors is not None:
                non_form_errors = non_form_errors()
            return HttpResponse(content=json.dumps({"valid": False,
                                                    "reason": "validation", "errors": form.errors, "non_form_errors": non_form_errors}),
                                content_type="application/json")

    def get_context_data(self, **kwargs):
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
        try:
            data['filecategoryform'] = FileCategoryForm(
                instance=self.request.user.file_category)
        except FileCategory.DoesNotExist:
            data['filecategoryform'] = FileCategoryForm()

        return data

    def form_invalid(self, **forms):
        return self.render_to_response(self.get_context_data(**forms))

    def form_valid(self, form):
        context = self.get_context_data()
        makerform = context['makerform']
        checkerform = context['checkerform']
        levelform = context['levelform']
        makerform_valid = False
        checkerform_valid = False
        levelform_valid = False
        with transaction.atomic():
            if makerform.is_valid():
                makerform_valid = True
                makerform.save()

            if checkerform.is_valid():
                checkerform_valid = True
                makerform.save()

            if levelform.is_valid():
                levelform_valid = True
                makerform.save()
        if all((levelform_valid, checkerform_valid, makerform_valid)):
            return super().form_valid(form)
        else:
            return self.form_invalid(makerform=makerform, checkerform=checkerform, levelform=levelform)

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = self.get_form_class()
        kwargs = self.get_form_kwargs()
        kwargs.pop('instance')
        return form_class(**kwargs)


class Members(RootRequiredMixin, ListView):
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


def delete(request):
    if request.is_ajax() and request.method == 'POST':
        try:
            data = request.POST.copy()
            user = User.objects.get(id=int(data['user_id']))
            user.delete()
            return HttpResponse(content=json.dumps({"valid": "true"}), content_type="application/json")
        except User.DoesNotExist:
            return HttpResponse(content=json.dumps({"valid": "false"}), content_type="application/json")
    else:
        raise Http404()


def levels(request):
    initial_query = Levels.objects.filter(
        created__hierarchy=request.user.hierarchy
    )

    if request.method == 'POST':

        form = LevelFormSet(
            request.POST,
            prefix='level',
            queryset=initial_query
        )
        if form and form.is_valid():

            objs = form.save(commit=False)
            try:
                for obj in form.deleted_objects:
                    obj.delete()
            except AttributeError:
                pass

            for obj in objs:
                obj.hierarchy = request.user.hierarchy
                obj.created_id = request.user.root.id
                try:
                    obj.save()
                except IntegrityError as e:
                    print('IntegrityError', e)
                    return HttpResponse(content=json.dumps({"valid": False, "reason": "integrity"}), content_type="application/json")

            payload = {"valid": True}

            return HttpResponse(content=json.dumps(payload), content_type="application/json")

        return HttpResponse(content=json.dumps({
            "valid": False,
            "reason": "validation",
            "errors": form.errors,
            "non_form_errors": form.non_form_errors()
        }), content_type="application/json")

    else:
        context = {
            'levelform': LevelFormSet(queryset=initial_query, prefix='level')
        }
        return render(request, 'users/add_levels.html', context)


class BaseAddMemberView(RootRequiredMixin, CreateView):
    template_name = 'users/add_member.html'

    def form_valid(self, form):
        self.object = form.save()
        self.object.hierarchy = self.request.user.hierarchy
        self.object.save()
        return super().form_valid(form)


class AddCheckerView(BaseAddMemberView):
    model = CheckerUser
    form_class = CheckerCreationForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {'who': 'checker', 'success_url': reverse_lazy("users:add_checker")})
        return context


class AddMakerView(BaseAddMemberView):
    model = MakerUser
    form_class = MakerCreationForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {'who': 'maker', 'success_url': reverse_lazy("users:add_maker")})
        return context


class ProfileView(DetailView):
    model = User
    template_name = 'users/profile.html'

    def get_object(self, queryset=None):
        return self.request.user


class ProfileUpdateView(UpdateView):
    model = User
    template_name = 'users/profile_update.html'
    form_class = ProfileEditForm

    def get_object(self, queryset=None):
        return self.request.user
