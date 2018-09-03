# from users.validators import ComplexPasswordValidator

from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth import password_validation
from django.contrib.auth.forms import UserChangeForm as AbstractUserChangeForm
from django.contrib.auth.models import Group
from django.utils.translation import ugettext_lazy as _

from users.models import User
from django import forms
from django.contrib.auth.forms import UserCreationForm


class SetPasswordForm(forms.Form):
    """
    A form that lets a user change set their password without entering the old
    password
    """
    password_widget = forms.TextInput(
        attrs={'class': 'form-control', 'type': 'password', 'autocomplete': 'off'})
    error_messages = {
        'password_mismatch': "The two passwords fields didn't match.",
        'weak_password': "Password must contain at least 8 characters",
    }
    new_password1 = forms.CharField(
        label="New password",
        widget=password_widget,
        strip=False,
        help_text=password_validation.password_validators_help_text_html(),
        # validators= [ComplexPasswordValidator],
    )
    new_password2 = forms.CharField(
        label="New password confirmation",
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
        'password_incorrect': "Your old password was entered incorrectly. Please enter it again.",
        'similar_password': "Your old password is similar to the new password. ",
    })
    old_password = forms.CharField(
        label="Old password",
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
            self.fields["users"].queryset = User.objects.all().exclude(username=self.request.user.username)

        elif self.request.user.is_parent:
            self.fields["users"].queryset = self.request.user.child()
            self.fields["name"].help_text = "Begin it with %s_ at first to avoid redundancy" % \
                                            self.request.user.username
            try:
                self.fields["permissions"].queryset = self.request.user.groups.first().permissions.all()
            except:
                pass

        if self.request.obj:
            self.fields["users"].initial = list(self.request.obj.user_set.all())

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
        elif self.request.user.is_parent:
            name = "%s_" % self.request.user.username + name
            return name

    def save(self, commit=True):
        group = super(GroupAdminForm, self).save(commit=False)
        # TODO: Check users save from group form or not
        group.hierarchy_id = self.request.user.hierarchy_id
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
        fields = '__all__'
        exclude = ('otp', )

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        if not self.request.user.is_superuser:
            self.fields["username"].help_text = "Begin it with %s_ at first to avoid redundancy" % \
                                                self.request.user.username

    def clean_email(self):
        email = self.cleaned_data['email']
        if email == '':
            self.add_error("email", "Email can't be blank")
        return email

    def clean_username(self):
        name = self.cleaned_data['username']
        if not self.request.user.is_superuser and self.request.user.username in name:
            return name
        elif self.request.user.is_superuser:
            return name
        elif self.request.user.is_parent:
            name = "%s_" % self.request.user.username + name
            return name

    def clean_arabic_name(self):
        ar_name = self.cleaned_data['arabic_name']
        if ar_name == '':
            return ar_name
        if langdetect.detect(ar_name) in ['ar', 'fa']:
            return ar_name
        else:
            raise forms.ValidationError(
                message=self.add_error(error='Name must be in arabic',
                                       field='arabic_name'
                                       ), code='invalid')

    def save(self, commit=True):
        user = super(UserForm, self).save(commit=False)
        if self.request.user.is_superuser:
            if user.is_superuser:
                user.hierarchy_id = 0

            else:
                maximum = max(User.objects.values_list('hierarchy_id', flat=True))
                try:
                    user.hierarchy_id = maximum + 1
                except TypeError:
                    user.hierarchy_id = 1
                user.is_root = True

        if self.request.user.is_root:
            user.hierarchy_id = self.request.user.hierarchy_id

        if commit:
            user.save()
        return user


class UserChangeForm(AbstractUserChangeForm):
    class Meta:
        model = User
        fields = '__all__'

    def clean_arabic_name(self):
        ar_name = self.cleaned_data['arabic_name']
        if ar_name == '':
            return ar_name
        if langdetect.detect(ar_name) in ['ar', 'fa']:
            return ar_name
        else:
            raise forms.ValidationError(
                message=self.add_error(error='Name must be in arabic',
                                       field='arabic_name'
                                       ), code='invalid')

    def clean_groups(self):
        form_groups = self.cleaned_data['groups']
        try:
            parent_joined_groups = self.instance.groups_joined().exclude(hierarchy_id=self.instance.hierarchy_id)
        except AttributeError:
            parent_joined_groups = BillsGroup.objects.none()
        groups = (form_groups | parent_joined_groups).distinct()
        return groups
