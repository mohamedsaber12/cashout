# from users.validators import ComplexPasswordValidator

from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth import password_validation
from django.contrib.auth.forms import UserChangeForm as AbstractUserChangeForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group
from django.forms import (BaseFormSet, BaseModelFormSet, formset_factory,
                          inlineformset_factory, modelformset_factory)
from django.utils.translation import ugettext_lazy as _

from users.models import CheckerUser, Levels, MakerUser, RootUser, User


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


class RootCreationForm(UserForm):
    class Meta(UserCreationForm.Meta):
        model = RootUser

    def __init__(self, *args, **kwargs):
        super(RootCreationForm, self).__init__(*args, **kwargs)
        if not self.request.user.is_superuser:
            self.fields["username"].help_text = "Begin it with %s_ at first to avoid redundancy" % \
                                                self.request.user.username

    def save(self, commit=True):
        user = super(UserForm, self).save(commit=False)
        if self.request.user.is_superuser:
            if user.is_superuser:
                user.hierarchy = 0

            else:
                maximum = max(RootUser.objects.values_list(
                    'hierarchy', flat=True))
                if not maximum:
                    maximum = 0
                try:
                    user.hierarchy = maximum + 1
                except TypeError:
                    user.hierarchy = 1
                user.user_type = 3

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
            parent_joined_groups = self.instance.groups_joined().exclude(
                hierarchy=self.instance.hierarchy)
        except AttributeError:
            parent_joined_groups = Group.objects.none()
        groups = (form_groups | parent_joined_groups).distinct()
        return groups


class LevelForm(forms.ModelForm):
    class Meta:
        model = Levels
        exclude = ('created',)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fields['level_of_authority'].choices = [
            (1, 'Level 1'), (2, 'Level 2'), (3, 'Level 3'), (4, 'Level 4')]


class BaseLevelFormSet(BaseModelFormSet):
    def clean(self):
        """Checks that no two levels are not same."""
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return
        level_of_authorities = []
        for form in self.forms:
            level_of_authority = form.cleaned_data['level_of_authority']
            if level_of_authority in level_of_authorities:
                raise forms.ValidationError(
                    "Articles in a set must have distinct titles.")
            level_of_authorities.append(level_of_authority)


class MakerCreationForm(forms.ModelForm):
    class Meta:
        model = MakerUser
        fields = ('username', 'first_name', 'last_name',
                  'mobile_no', 'email', 'is_staff')

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
    def __init__(self, *args, request, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["level"].choices = [('', '------')] + [
            (r.id, str(r)) for r in Levels.objects.filter(created__hierarchy=request.user.hierarchy)
            ]

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
        user.user_type = 2
        if commit:
            user.save()
        return user

    class Meta:
        model = CheckerUser
        fields = ['username', 'first_name', 'last_name',
                  'email', 'mobile_no', 'level', 'is_staff']


LevelFormSet = modelformset_factory(
    model=Levels, form=LevelForm, formset=BaseLevelFormSet, max_num=4, min_num=1, can_delete=True, validate_max=True, extra=0)

MakerMemberFormSet = modelformset_factory(
    model=MakerUser, form=MakerCreationForm, can_delete=True)

CheckerMemberFormSet = modelformset_factory(
    model=CheckerUser, form=CheckerCreationForm, can_delete=True)
