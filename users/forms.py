# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy

from django import forms
from django.conf import settings
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth import password_validation
from django.contrib.auth.forms import UserChangeForm as AbstractUserChangeForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.forms import modelformset_factory
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _
from django_otp.forms import OTPAuthenticationFormMixin

from .models import Brand, CheckerUser, Client, EntitySetup, Levels, MakerUser, RootUser, UploaderUser, User
from .signals import ALLOWED_CHARACTERS


class SetPasswordForm(forms.Form):
    """
    A form that lets a user change set their password without entering the old
    password
    """
    password_widget = forms.TextInput(attrs={'class': 'form-control', 'type': 'password', 'autocomplete': 'off'})
    error_messages = {
        'password_mismatch': _("The two passwords fields didn't match."),
        'weak_password': _("Password must contain at least 8 characters"),
    }
    new_password1 = forms.CharField(
        label=_("New password"),
        widget=password_widget,
        strip=False,
        help_text=password_validation.password_validators_help_text_html(),
        # validators= [users.validators.ComplexPasswordValidator],
    )
    new_password2 = forms.CharField(
        label=_("New password confirmation"),
        strip=False,
        widget=password_widget,
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(SetPasswordForm, self).__init__(*args, **kwargs)

    def clean_new_password2(self):
        """Clean password2 against password1"""
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(self.error_messages['password_mismatch'], code='password_mismatch')
        if len(password1) < 8:
            raise forms.ValidationError(self.error_messages['weak_password'], code='weak_password')

        password_validation.validate_password(password2, self.user)
        return password2

    def save(self, commit=True):
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user


class PasswordChangeForm(SetPasswordForm):
    """
    A form that lets a user change their password by entering their old
    password.
    """
    password_widget = forms.TextInput(attrs={'class': 'form-control', 'type': 'password', 'autocomplete': 'off'})
    error_messages = dict(SetPasswordForm.error_messages, **{
        'password_incorrect': _("Your old password was entered incorrectly. Please enter it again."),
        'similar_password': _("Your old password is similar to the new password. "),
    })
    old_password = forms.CharField(label=_("Old password"), strip=False, widget=password_widget,)
    field_order = ['old_password', 'new_password1', 'new_password2']

    def clean_new_password2(self):
        """Clean password2 against password1 and the old password"""
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        old_password = self.cleaned_data.get('old_password')

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(self.error_messages['password_mismatch'], code='password_mismatch')
        if old_password == password2:
            raise forms.ValidationError(self.error_messages['similar_password'], code='similar_password')
        if len(password1) < 8:
            raise forms.ValidationError(self.error_messages['weak_password'], code='weak_password')

        password_validation.validate_password(password2, self.user)
        return password2

    def clean_old_password(self):
        """Validates that the old_password field is correct"""
        old_password = self.cleaned_data["old_password"]

        if not self.user.check_password(old_password):
            raise forms.ValidationError(self.error_messages['password_incorrect'], code='password_incorrect')
        return old_password


class GroupAdminForm(forms.ModelForm):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=FilteredSelectMultiple(verbose_name=_('Users'), is_stacked=False)
    )

    def __init__(self, *args, **kwargs):
        super(GroupAdminForm, self).__init__(*args, **kwargs)

        if self.request.user.is_superuser:
            self.fields["users"].queryset = User.objects.all().exclude(username=self.request.user.username)
        elif self.request.user.is_root:
            self.fields["users"].queryset = self.request.user.children()
            self.fields["name"].help_text = f"Begin it with {self.request.user.username}_ at first to avoid redundancy"
            try:
                self.fields["permissions"].queryset = self.request.user.groups.first().permissions.all()
            except:
                pass
        if self.request.obj:
            self.fields["users"].initial = list(self.request.obj.user_set.all())

    class Meta:
        model = Group
        fields = ['name', 'users', 'permissions']

    def clean_name(self):
        name = self.cleaned_data['name']
        if not self.request.user.is_superuser and self.request.user.username in name:
            return name
        elif self.request.user.is_superuser:
            return name
        elif self.request.user.is_root:
            name = "%s_" % self.request.user.username + name
            return name

    def save(self, commit=True):
        group = super(GroupAdminForm, self).save(commit=False)
        # TODO: Check users save from group form or not
        group.hierarchy = self.request.user.hierarchy
        group.save()
        if group.pk:
            user_choices = self.cleaned_data['users']
            group.user_set.clear()
            for user in user_choices:
                group.user_set.add(user)

            self.save_m2m()

        return group


class UserForm(UserCreationForm):
    class Meta:
        model = User
        exclude = ['otp', 'hierarchy']

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)

        if not self.request.user.is_superuser:
            self.fields["username"].help_text = f"Begin it with {self.request.user}_ at first to avoid redundancy"
            try:
                self.fields.pop("parent")
            except KeyError:
                pass

    def clean_username(self):
        name = self.cleaned_data['username']
        if not self.request.user.is_superuser and self.request.user.username in name:
            return name
        elif self.request.user.is_superuser:
            return name
        elif self.request.user.is_root:
            name = "%s_" % self.request.user.username + name
            return name


class AbstractChildrenCreationForm(UserForm):
    parent = forms.ModelChoiceField(queryset=RootUser.objects.all())


class MakerCreationAdminForm(AbstractChildrenCreationForm):
    """
    Maker creation form for admin usage only
    """
    class Meta(UserCreationForm.Meta):
        model = MakerUser


class CheckerCreationAdminForm(AbstractChildrenCreationForm):
    """
    Root Creation form for admin usage only
    """
    class Meta(UserCreationForm.Meta):
        model = CheckerUser


class RootCreationForm(forms.ModelForm):
    """
    Admin/Root on-boarding form
    """

    class Meta:
        model = RootUser
        fields = ['username', 'email']
        field_classes = {}

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(RootCreationForm, self).__init__(*args, **kwargs)

        for field in self.fields:
            self.fields[field].widget.attrs.setdefault('placeholder', self.fields[field].label)

    def clean_username(self):
        name = self.cleaned_data['username']
        return name

    def define_new_admin_hierarchy(self, new_user):
        """
        Generate/Define the hierarchy of the new admin user
        :param new_user: the new admin user to be created
        :return: the new admin user with its new hierarchy
        """
        maximum = max(RootUser.objects.values_list('hierarchy', flat=True), default=False)
        maximum = 0 if not maximum else maximum

        try:
            new_user.hierarchy = maximum + 1
        except TypeError:
            new_user.hierarchy = 1

        return new_user

    def save(self, commit=True):
        user = super().save(commit=False)
        temporary_random_password = get_random_string(allowed_chars=ALLOWED_CHARACTERS, length=12)
        user.set_password(temporary_random_password)

        if self.request.user.is_superadmin:
            user.user_type = 3
            user = self.define_new_admin_hierarchy(user)

        if self.request.user.is_root:
            user.hierarchy = self.request.user.hierarchy

        user.save()
        return user


class UserChangeForm(AbstractUserChangeForm):

    class Meta:
        model = User
        fields = '__all__'

    def clean_groups(self):
        form_groups = self.cleaned_data['groups']
        try:
            parent_joined_groups = self.instance.groups_joined().exclude(hierarchy=self.instance.hierarchy)
        except AttributeError:
            parent_joined_groups = Group.objects.none()
        groups = (form_groups | parent_joined_groups).distinct()
        return groups


class ProfileEditForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'mobile_no', 'email', 'title', 'avatar_thumbnail']


class LevelForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, ** kwargs)

    class Meta:
        model = Levels
        exclude = ['created', 'level_of_authority']

    def clean_max_amount_can_be_disbursed(self):
        amount = self.cleaned_data.get('max_amount_can_be_disbursed')

        if not amount and amount != 0:
            return amount

        if amount <= 0:
            raise forms.ValidationError(_('Amount must be greater than 0'))

        levels_qs = Levels.objects.filter(created=self.request.user, max_amount_can_be_disbursed=amount)
        if self.instance and self.instance.id:
            levels_qs = levels_qs.exclude(id=self.instance.id)

        if levels_qs.exists():
            raise forms.ValidationError(_('Level with this amount already exist'))
        return amount

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.created = self.request.user.root
        if commit:
            instance.save()
        return instance


class MakerCreationForm(forms.ModelForm):

    first_name = forms.CharField(label=_('First name'))
    last_name = forms.CharField(label=_('Last name'))

    class Meta:
        model = MakerUser
        fields = ['first_name', 'last_name', 'mobile_no', 'email']

    def __init__(self, *args, request, **kwargs):
        super().__init__(*args, **kwargs)

        for field in iter(self.fields):
            # get current classes from Meta
            classes = self.fields[field].widget.attrs.get("class")
            if field == 'is_staff':
                if classes is not None:
                    classes += " icheckbox_flat-green checked"
                else:
                    classes = "icheckbox_flat-green"
                self.fields[field].widget.attrs.update({'class': classes})
            else:
                if classes is not None:
                    classes += " form-control"
                else:
                    classes = "form-control"
                self.fields[field].widget.attrs.update({'class': classes})
        self.request = request

    def clean_email(self):
        email = self.cleaned_data.get('email')
        uploader = UploaderUser.objects.filter(email=email).first()
        if uploader and uploader.data_type() == 3:
            uploader.user_type = 5
            self.instance_copy = copy.copy(uploader)
            self.instance = uploader

        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        if user.user_type != 5:
            user.user_type = 1
        else:
            user = self.instance_copy

        user.hierarchy = self.request.user.hierarchy

        if commit:
            user.save()
            user.user_permissions.add(*Permission.objects.filter(user=self.request.user))
        return user


class CheckerCreationForm(forms.ModelForm):

    first_name = forms.CharField(label=_('First name'))
    last_name = forms.CharField(label=_('Last name'))

    def __init__(self, *args, request, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["level"].choices = [('', '------')] + [
            (r.id, f'{r}') for r in Levels.objects.filter(
                created__hierarchy=request.user.hierarchy).order_by('max_amount_can_be_disbursed')
        ]

        self.fields["level"].label = _('Level')

        for field in iter(self.fields):
            # get current classes from Meta
            classes = self.fields[field].widget.attrs.get("class")
            if classes is not None:
                classes += " form-control"
            else:
                classes = "form-control"
            self.fields[field].widget.attrs.update({'class': classes})
        self.request = request

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 2

        user.hierarchy = self.request.user.hierarchy

        if commit:
            user.save()
            user.user_permissions.add(*Permission.objects.filter(user=self.request.user))
        return user

    class Meta:
        model = CheckerUser
        fields = ['first_name', 'last_name', 'email', 'mobile_no', 'level']


class UploaderCreationForm(forms.ModelForm):

    first_name = forms.CharField(label=_('First name'))
    last_name = forms.CharField(label=_('Last name'))

    def __init__(self, *args, request, **kwargs):
        super().__init__(*args, **kwargs)

        for field in iter(self.fields):
            # get current classes from Meta
            classes = self.fields[field].widget.attrs.get("class")
            if classes is not None:
                classes += " form-control"
            else:
                classes = "form-control"
            self.fields[field].widget.attrs.update({'class': classes})
        self.request = request

    def clean_email(self):
        email = self.cleaned_data.get('email')
        maker = MakerUser.objects.filter(email=email).first()
        if maker and maker.data_type() == 3:
            maker.user_type = 5
            self.instance_copy = copy.copy(maker)
            self.instance = maker

        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        if user.user_type != 5:
            user.user_type = 4
        else:
            user = self.instance_copy

        user.hierarchy = self.request.user.hierarchy

        if commit:
            user.save()
            user.user_permissions.add(*Permission.objects.filter(user=self.request.user))
        return user

    class Meta:
        model = UploaderUser
        fields = ['first_name', 'last_name', 'email', 'mobile_no']


class BrandForm(forms.ModelForm):

    def __init__(self, *args, request, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request

    color = forms.CharField(widget=forms.HiddenInput())

    class Meta:
        model = Brand
        fields = "__all__"

    def save(self, commit=True):
        brand = super().save(commit=False)
        if commit:
            brand.save()
            self.request.user.brand = brand
            self.request.user.save()
        return brand


LevelFormSet = modelformset_factory(
        model=Levels, form=LevelForm, min_num=1, max_num=4, validate_min=True, validate_max=True, can_delete=True,
        extra=0
)

MakerMemberFormSet = modelformset_factory(
        model=MakerUser, form=MakerCreationForm, min_num=1, validate_min=True, can_delete=True, extra=0
)

CheckerMemberFormSet = modelformset_factory(
        model=CheckerUser, form=CheckerCreationForm, min_num=1, validate_min=True, can_delete=True, extra=0
)

UploaderMemberFormSet = modelformset_factory(
        model=UploaderUser, form=UploaderCreationForm, min_num=1, validate_min=True, can_delete=True, extra=0
)


class OTPTokenForm(OTPAuthenticationFormMixin, forms.Form):
    """
    A form that verifies an authenticated user. It looks very much like
    :class:`~django_otp.forms.OTPAuthenticationForm`, but without the username
    and password. The first argument must be an authenticated user; you can use
    this in place of :class:`~django.contrib.auth.forms.AuthenticationForm` by
    currying it::

        from functools import partial

        from django.contrib.auth.decoratorrs import login_required
        from django.contrib.auth.views import login


        @login_required
        def verify(request):
            form_cls = partial(OTPTokenForm, request.user)

            return login(request, template_name='my_verify_template.html', authentication_form=form_cls)


    This form will ask the user to choose one of their registered devices and
    enter an OTP token. Validation will succeed if the token is verified. See
    :class:`~django_otp.forms.OTPAuthenticationForm` for details on writing a
    compatible template (leaving out the username and password, of course).

    :param user: An authenticated user.
    :type user: :class:`~django.contrib.auth.models.User`

    :param request: The current request.
    :type request: :class:`~django.http.HttpRequest`
    """
    # otp_device = forms.ChoiceField(choices=[])
    otp_token = forms.CharField(required=False)
    # otp_challenge = forms.CharField(required=False)

    def __init__(self, user, request=None, *args, **kwargs):
        super(OTPTokenForm, self).__init__(*args, **kwargs)

        self.user = user
        # self.fields['otp_device'].choices = self.device_choices(user)

    def clean(self):
        super(OTPTokenForm, self).clean()

        self.clean_otp(self.user)

        return self.cleaned_data

    def get_user(self):
        return self.user


class ForgotPasswordForm(forms.Form):

    email = forms.EmailField(label='')
    email2 = forms.EmailField(label='')
    email.widget.attrs.update({'class': 'form-control', 'placeholder': _('Email')})
    email2.widget.attrs.update({'class': 'form-control', 'placeholder': _('Confirm Email')})

    def clean(self):
        email = self.cleaned_data.get('email')
        email2 = self.cleaned_data.get('email2')
        if not(email and email2):
            return
        if email != email2:
            raise forms.ValidationError("Emails don't match")
        else:
            user_qs = User.objects.filter(email=email)
            if not user_qs.exists():
                raise forms.ValidationError("No user with this email exists")
            self.user = user_qs.first()

    def send_email(self):
        MESSAGE = 'Dear <strong>{0}</strong><br><br>' \
            'Please follow <a href="{1}" ><strong>this link</strong></a> to reset password, <br>' \
            'Then login with your username: <strong>{2}</strong> and your new password <br><br>' \
            'Thanks, BR'

        # one time token
        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk)).decode("utf-8")
        url = settings.BASE_URL + reverse('users:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})

        from_email = settings.SERVER_EMAIL
        sub_subject = f'[{self.user.brand.mail_subject}]'
        subject = "{}{}".format(sub_subject, _(' Password Notification'))
        recipient_list = [self.user.email]
        message = MESSAGE.format(self.user.first_name or self.user.username, url, self.user.username)
        mail_to_be_sent = EmailMultiAlternatives(subject, message, from_email, recipient_list)
        mail_to_be_sent.attach_alternative(message, "text/html")
        mail_to_be_sent.send()


class ClientFeesForm(forms.ModelForm):
    """
    Form for add client fees profile at the client on-boarding phase
    """

    CHOICES = ((100, 'Full'), (50, 'half'), (0, 'No fees'))
    fees_percentage = forms.ChoiceField(label=_("Fees"), widget=forms.Select, choices=CHOICES)

    class Meta:
        model = Client
        fields = ('fees_percentage',)

    def save(self, commit=True):
        client = super().save(commit=False)
        if commit:
            client.save()
            entity_setup = EntitySetup.objects.get(entity=client.client)
            entity_setup.fees_setup = True
            entity_setup.save()
        return client


class CustomClientProfilesForm(forms.ModelForm):
    """
    Form for updating client fees profile for those clients with custom budgets
    """

    class Meta:
        model = Client
        fields = ['custom_profile']
