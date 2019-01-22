# from users.validators import ComplexPasswordValidator

from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth import password_validation
from django.contrib.auth.forms import UserChangeForm as AbstractUserChangeForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group
from django.forms import (BaseFormSet, BaseModelFormSet, formset_factory,
                          inlineformset_factory, modelformset_factory)
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _

from users.models import CheckerUser, Levels, MakerUser, RootUser, User, Brand
from users.signals import ALLOWED_CHARACTERS


class SetPasswordForm(forms.Form):
    """
    A form that lets a user change set their password without entering the old
    password
    """
    password_widget = forms.TextInput(
        attrs={'class': 'form-control', 'type': 'password', 'autocomplete': 'off'})
    error_messages = {
        'password_mismatch': _("The two passwords fields didn't match."),
        'weak_password': _("Password must contain at least 8 characters"),
    }
    new_password1 = forms.CharField(
        label=_("New password"),
        widget=password_widget,
        strip=False,
        help_text=password_validation.password_validators_help_text_html(),
        # validators= [ComplexPasswordValidator],
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
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError(
                    self.error_messages['password_mismatch'],
                    code='password_mismatch',
                )
        if len(password1) < 8:
            raise forms.ValidationError(
                self.error_messages['weak_password'],
                code='weak_password',
            )
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
    password_widget = forms.TextInput(
        attrs={'class': 'form-control', 'type': 'password', 'autocomplete': 'off'})
    error_messages = dict(SetPasswordForm.error_messages, **{
        'password_incorrect': _("Your old password was entered incorrectly. Please enter it again."),
        'similar_password': _("Your old password is similar to the new password. "),
    })
    old_password = forms.CharField(
        label=_("Old password"),
        strip=False,
        widget=password_widget,
    )
    field_order = ['old_password', 'new_password1', 'new_password2']

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        old_password = self.cleaned_data.get('old_password')
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError(
                    self.error_messages['password_mismatch'],
                    code='password_mismatch',
                )
        if old_password == password2:
            raise forms.ValidationError(
                self.error_messages['similar_password'],
                code='similar_password',
            )
        if len(password1) < 8:
            raise forms.ValidationError(
                self.error_messages['weak_password'],
                code='weak_password',
            )
        password_validation.validate_password(password2, self.user)
        return password2

    def clean_old_password(self):
        """
        Validates that the old_password field is correct.
        """
        old_password = self.cleaned_data["old_password"]
        if not self.user.check_password(old_password):
            raise forms.ValidationError(
                self.error_messages['password_incorrect'],
                code='password_incorrect',
            )
        return old_password


class GroupAdminForm(forms.ModelForm):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=FilteredSelectMultiple(
            verbose_name=_('Users'),
            is_stacked=False
        )
    )

    def __init__(self, *args, **kwargs):
        super(GroupAdminForm, self).__init__(*args, **kwargs)
        if self.request.user.is_superuser:
            self.fields["users"].queryset = User.objects.all().exclude(
                username=self.request.user.username)

        elif self.request.user.is_root:
            self.fields["users"].queryset = self.request.user.child()
            self.fields["name"].help_text = "Begin it with %s_ at first to avoid redundancy" % \
                                            self.request.user.username
            try:
                self.fields["permissions"].queryset = self.request.user.groups.first(
                ).permissions.all()
            except:
                pass

        if self.request.obj:
            self.fields["users"].initial = list(
                self.request.obj.user_set.all())

    class Meta:
        model = Group
        fields = [
            'name',
            'users',
            'permissions',
        ]

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
        exclude = ('otp', 'hierarchy')

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        if not self.request.user.is_superuser:
            self.fields["username"].help_text = "Begin it with %s_ at first to avoid redundancy" % \
                                                self.request.user.username
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
    class Meta:
        model = RootUser
        fields = ("username", "email")
        field_classes = {}

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(RootCreationForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.setdefault('placeholder', self.fields[field].label)

    def clean_username(self):
        name = self.cleaned_data['username']
        return name

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.request.user.is_superadmin:
            maximum = max(RootUser.objects.values_list(
                'hierarchy', flat=True), default=False)
            if not maximum:
                maximum = 0
            try:
                user.hierarchy = maximum + 1
            except TypeError:
                user.hierarchy = 1
            user.user_type = 3

        if self.request.user.is_root:
            user.hierarchy = self.request.user.hierarchy
        random_pass = get_random_string(
            allowed_chars=ALLOWED_CHARACTERS, length=12)
        user.set_password(random_pass)
        user.save()
        return user


class UserChangeForm(AbstractUserChangeForm):
    class Meta:
        model = User
        fields = '__all__'

    def clean_groups(self):
        form_groups = self.cleaned_data['groups']
        try:
            parent_joined_groups = self.instance.groups_joined().exclude(
                hierarchy=self.instance.hierarchy)
        except AttributeError:
            parent_joined_groups = Group.objects.none()
        groups = (form_groups | parent_joined_groups).distinct()
        return groups


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "mobile_no",
                  "email", "title", "avatar_thumbnail")


class LevelForm(forms.ModelForm):
    class Meta:
        model = Levels
        exclude = ('created', 'level_of_authority')



class MakerCreationForm(forms.ModelForm):
    first_name = forms.CharField(label=_('First name'))
    last_name = forms.CharField(label=_('Last name'))

    class Meta:
        model = MakerUser
        fields = ('first_name', 'last_name',
                  'mobile_no', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in iter(self.fields):
            # get current classes from Meta
            classes = self.fields[field].widget.attrs.get("class")
            if field == 'is_staff':
                if classes is not None:
                    classes += " icheckbox_flat-green checked"
                else:
                    classes = "icheckbox_flat-green"
                self.fields[field].widget.attrs.update({
                    'class': classes
                })
            else:
                if classes is not None:
                    classes += " form-control"
                else:
                    classes = "form-control"
                self.fields[field].widget.attrs.update({
                    'class': classes
                })

    def save(self, commit=True):

        user = super().save(commit=False)
        user.user_type = 1
        if commit:
            user.save()
        return user


class CheckerCreationForm(forms.ModelForm):
    first_name = forms.CharField(label=_('First name'))
    last_name = forms.CharField(label=_('Last name'))

    def __init__(self, *args, request, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["level"].choices = [('', '------')] + [
            (r.id, f'{r} {i+1}') for i, r in enumerate(Levels.objects.filter(created__hierarchy=request.user.hierarchy).order_by('max_amount_can_be_disbursed'))
        ]

        self.fields["level"].label = _('Level')

        for field in iter(self.fields):
            # get current classes from Meta
            classes = self.fields[field].widget.attrs.get("class")
            if classes is not None:
                classes += " form-control"
            else:
                classes = "form-control"
            self.fields[field].widget.attrs.update({
                'class': classes
            })

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 2
        if commit:
            user.save()
        return user

    class Meta:
        model = CheckerUser
        fields = ['first_name', 'last_name',
                  'email', 'mobile_no', 'level']


class BrandForm(forms.ModelForm):
    def __init__(self, *args, request, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request

    color = forms.CharField(widget=forms.HiddenInput())
    class Meta:
        model = Brand
        fields = ("color", "logo")

    def save(self, commit=True):
        brand = super().save(commit=False)
        if commit:
            brand.save()
            self.request.user.brand = brand
            self.request.user.save()
        return brand

LevelFormSet = modelformset_factory(
    model=Levels, form=LevelForm,  max_num=4,
    min_num=1, can_delete=True, extra=1, validate_min=True, validate_max=True
)

MakerMemberFormSet = modelformset_factory(
    model=MakerUser, form=MakerCreationForm, 
    min_num=1, validate_min=True, can_delete=True, extra=1)

CheckerMemberFormSet = modelformset_factory(
    model=CheckerUser, form=CheckerCreationForm, 
    min_num=1, validate_min=True, can_delete=True, extra=1)

from django_otp.forms import OTPAuthenticationFormMixin
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
    #otp_device = forms.ChoiceField(choices=[])
    otp_token = forms.CharField(required=False)
    #otp_challenge = forms.CharField(required=False)

    def __init__(self, user, request=None, *args, **kwargs):
        super(OTPTokenForm, self).__init__(*args, **kwargs)

        self.user = user
        #self.fields['otp_device'].choices = self.device_choices(user)

    def clean(self):
        super(OTPTokenForm, self).clean()

        self.clean_otp(self.user)

        return self.cleaned_data

    def get_user(self):
        return self.user
