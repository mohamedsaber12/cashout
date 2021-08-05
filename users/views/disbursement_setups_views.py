# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import Permission
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import CreateView, FormView, TemplateView

from data.forms import FileCategoryFormSet
from data.models import FileCategory
from disbursement.forms import PinForm

from ..forms import CheckerCreationForm, CheckerMemberFormSet, LevelFormSet, MakerCreationForm, MakerMemberFormSet
from ..mixins import DisbursementRootRequiredMixin
from ..models import CheckerUser, Levels, MakerUser, Setup


class BaseFormsetView(TemplateView):
    """
    BaseView for setup Formsets
    """

    manual_setup = None

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
        if self.manual_setup is None:
            self.manual_setup = Setup.objects.get(user__hierarchy=self.request.user.hierarchy)
        return self.manual_setup

    def form_valid(self, form):
        form.save()
        manual_setup = self.get_setup()
        setattr(manual_setup, f'{self.setup_key}_setup', True)
        manual_setup.save()
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


class PinFormView(DisbursementRootRequiredMixin, FormView):
    """
    Pin form view for the on-boarding phase of an entity/root
    """

    template_name = 'users/setting-up-disbursement/pin.html'
    manual_setup = None

    def get(self, request, *args, **kwargs):
        """Handle GET requests: instantiate a blank version of the form."""
        if request.GET.get('q', None) == 'next':
            manual_setup = self.get_setup()
            if manual_setup.pin_setup:
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
            manual_setup = self.get_setup()
            manual_setup.pin_setup = True
            manual_setup.save()
            return self.form_valid(form)
        return self.form_invalid(form)

    def get_setup(self):
        if self.manual_setup is None:
            self.manual_setup = Setup.objects.get(user__hierarchy=self.request.user.hierarchy)
        return self.manual_setup

    def get_success_url(self):
        to_step = self.request.GET.get('to_step', None)
        if to_step == '3':
            return reverse('users:setting-disbursement-levels')
        if to_step == '4':
            return reverse('users:setting-disbursement-checkers')
        if to_step == '5':
            return reverse('users:setting-disbursement-formats')

        return reverse('users:setting-disbursement-makers')


class MakerFormView(DisbursementRootRequiredMixin, BaseFormsetView):
    """
    Maker FormView for handling the on-boarding phase of makers for a new entity
    """

    template_name = 'users/setting-up-disbursement/makers.html'
    form_class = MakerMemberFormSet
    model = MakerUser
    prefix = 'maker'
    setup_key = 'maker'
    data_type = 'disbursement'

    def get(self, request, *args, **kwargs):
        """Handle GET requests"""
        manual_setup = self.get_setup()
        if not manual_setup.pin_setup:
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
    """
    Checker FormView for handling the on-boarding phase of checkers for a new entity
    """

    template_name = 'users/setting-up-disbursement/checkers.html'
    form_class = CheckerMemberFormSet
    model = CheckerUser
    prefix = 'checker'
    setup_key = 'checker'
    data_type = 'disbursement'

    def get(self, request, *args, **kwargs):
        """Handle GET requests"""
        manual_setup = self.get_setup()
        if not manual_setup.levels_setup:
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
    """
    Levels of disbursement FormView for handling the on-boarding phase of checkers for a new entity
    """

    template_name = 'users/setting-up-disbursement/levels.html'
    form_class = LevelFormSet
    model = Levels
    prefix = 'level'
    data_type = 'disbursement'

    def get(self, request, *args, **kwargs):
        """Handle GET requests"""

        manual_setup = self.get_setup()
        if not manual_setup.maker_setup:
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
        manual_setup = self.get_setup()
        manual_setup.levels_setup = True
        manual_setup.save()
        return redirect(self.get_success_url())


class CategoryFormView(DisbursementRootRequiredMixin, BaseFormsetView):
    """
    Category FormView is for the on-boarding phase of the to-be-uploaded sheet specs for a new entity
    """

    template_name = 'users/setting-up-disbursement/category.html'
    form_class = FileCategoryFormSet
    model = FileCategory
    prefix = 'category'
    setup_key = 'category'
    data_type = 'disbursement'

    def get(self, request, *args, **kwargs):
        """Handle GET requests"""
        manual_setup = self.get_setup()
        if not manual_setup.checker_setup:
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

        return reverse('data:e_wallets_home')

    def get_queryset(self):
        return self.model.objects.filter(user_created__hierarchy=self.request.user.hierarchy)


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
