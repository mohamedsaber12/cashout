# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView, TemplateView

from data.forms import CollectionDataForm, FormatFormSet
from data.models import Format

from ..forms import UploaderMemberFormSet
from ..mixins import CollectionRootRequiredMixin
from ..models import Setup, UploaderUser


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


class CollectionFormView(CollectionRootRequiredMixin, FormView):
    """

    """

    template_name = 'users/setting-up-collection/collection.html'
    manual_setup = None

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
            manual_setup = self.get_setup()
            manual_setup.collection_setup = True
            manual_setup.save()
            form.save()
            return self.form_valid(form)
        return self.form_invalid(form)

    def get_setup(self):
        if self.manual_setup is None:
            self.manual_setup = Setup.objects.get(user__hierarchy=self.request.user.hierarchy)
        return self.manual_setup

    def get_success_url(self):
        to_step = self.request.GET.get('to_step', None)
        if to_step == '3':
            return reverse('users:setting-collection-uploader')

        return reverse('users:setting-collection-formats')


class FormatFormView(CollectionRootRequiredMixin, BaseFormsetView):
    """

    """

    template_name = 'users/setting-up-collection/formats.html'
    form_class = FormatFormSet
    model = Format
    prefix = 'format'
    setup_key = 'format_collection'
    data_type = 'collection'

    def get(self, request, *args, **kwargs):
        """Handle GET requests"""
        manual_setup = self.get_setup()
        if not manual_setup.collection_setup:
            return reverse('users:setting-collection-collectiondata')
        return self.render_to_response(self.get_context_data())

    def get_success_url(self):
        to_step = self.request.GET.get('to_step', None)
        if to_step == '1':
            return reverse('users:setting-collection-collectiondata')

        return reverse('users:setting-collection-uploader')

    def get_queryset(self):
        return self.model.objects.filter(hierarchy=self.request.user.hierarchy)


class UploaderFormView(CollectionRootRequiredMixin, BaseFormsetView):
    """

    """

    template_name = 'users/setting-up-collection/uploader.html'
    form_class = UploaderMemberFormSet
    model = UploaderUser
    prefix = 'uploader'
    setup_key = 'uploaders'
    data_type = 'collection'

    def get(self, request, *args, **kwargs):
        """Handle GET requests"""
        manual_setup = self.get_setup()
        if not manual_setup.format_collection_setup:
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
