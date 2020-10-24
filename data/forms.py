# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import os
import tempfile

import xlrd

from django import forms
from django.core.validators import FileExtensionValidator
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from users.models import User
from utilities.messages import MSG_WRONG_FILE_FORMAT
from utilities.models import AbstractBaseDocType

from .models import CollectionData, Doc, DocReview, FileCategory, Format


UPLOAD_ERROR_LOGGER = logging.getLogger("upload_error")

TASK_UPLOAD_FILE_TYPES = [
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
    'text/plain',
    'text/csv',
    'csv',
    'msword',
    'vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'vnd.openxmlformats-officedocument.wordprocessingml.document',
    'vnd.ms-excel',
]
MIME_UPLOAD_FILE_TYPES = ['plain', 'octet-stream']
TASK_UPLOAD_FILE_MAX_SIZE = 5242880
UNICODE = set(';:></*%$.\\')


class FileDocumentForm(forms.ModelForm):
    """
    A form for uploading files
    """

    file = forms.FileField(
        label=_('Select a file'),
        help_text=_('max. 42 megabytes'),
        validators=[FileExtensionValidator(allowed_extensions=['xls', 'xlsx', 'csv', 'txt', 'doc', 'docx'])]
    )

    class Meta:
        model = Doc
        fields = ['file_category', 'format', 'file']

    def __init__(self, *args, **kwargs):
        """
        Initialize FileDocumentForm for uploading files.
        :param kwargs: request and (is_disbursement or collection) only one of them
        """
        self.request = kwargs.pop('request')
        self.is_disbursement = kwargs.pop('is_disbursement', False)
        self.collection = kwargs.pop('collection', None)

        super().__init__(*args, **kwargs)

        if self.is_disbursement:
            self.type_of = AbstractBaseDocType.E_WALLETS
            del self.fields['format']
        else:
            self.type_of = AbstractBaseDocType.COLLECTION
            del self.fields['file_category']

    def extract_file_type(self, file):
        """
        :param file: uploaded file object
        :return: file type/extension
        """
        file_type = file.content_type.split('/')[1]
        number_of_dots = len(file.name.split('.'))

        if number_of_dots != 2:
            raise forms.ValidationError(_("File type is not supported"))
        return file_type

    def extract_file_name(self, file):
        """
        :param file: uploaded file object
        :return: file name without the extension
        """
        try:
            filename = "".join(file.name.split('.')[:-1])
        except ValueError:
            raise forms.ValidationError(_("File name is not proper"))

        return filename

    def validate_file_type_size_and_name(self, file):
        """
        :param file: uploaded file object
        :return: Raise form validation error if there is any problem with file type, size or name else returns True
        """
        file_type = self.extract_file_type(file)
        filename = self.extract_file_name(file)
        error = False

        if any((char in UNICODE) for char in filename):
            error = "Filename should not include any unicode characters ex: >, <, /, $, * "

        elif file_type not in TASK_UPLOAD_FILE_TYPES or 'openxml' not in file_type:
            error = "File type is not supported"

        elif file.size > TASK_UPLOAD_FILE_MAX_SIZE:
            error = "Please keep file size under 5242880"

        elif len(file.name.split('.')[0]) > 100:
            error = "Filename must be less than 255 characters"

        if error:
            msg = f"file name: {filename}, file type: {file_type}, file size: {file.size}, error: {error}"
            UPLOAD_ERROR_LOGGER.debug(f"[message] [UPLOAD ERROR AT FORM VALIDATION] [{self.request.user}] -- {msg}")
            raise forms.ValidationError(_(error))

        return True

    def write_file_to_disk(self, file, format_type, file_category):
        """
        :param file: uploaded file object
        :param format_type: format defined for the uploader user of a collection file
        :param file_category: file category selected at uploading a disbursement file
        :return: the file uploaded written to the disk
        """
        try:
            fd, tmp = tempfile.mkstemp()
            with os.fdopen(fd, 'wb') as out:
                out.write(file.read())

            if self.is_disbursement:
                try:
                    xl_workbook = xlrd.open_workbook(tmp)
                except Exception:
                    raise forms.ValidationError(_(MSG_WRONG_FILE_FORMAT))
                xl_sheet = xl_workbook.sheet_by_index(0)

                if file_category.unique_identifiers_number > xl_sheet.ncols:
                    raise forms.ValidationError(_(MSG_WRONG_FILE_FORMAT))

            elif format_type and format_type.num_of_identifiers != 0:
                try:
                    xl_workbook = xlrd.open_workbook(tmp)
                except Exception:
                    raise forms.ValidationError(_(MSG_WRONG_FILE_FORMAT))
                xl_sheet = xl_workbook.sheet_by_index(0)

                if len(format_type.identifiers()) != xl_sheet.ncols:
                    raise forms.ValidationError(_(MSG_WRONG_FILE_FORMAT))

                # validate headers
                cell_obj = next(xl_sheet.get_rows())
                headers = [data.value for data in cell_obj]
                if not format_type.headers_match(headers):
                    raise forms.ValidationError(_("File headers doesn't match the format identifiers"))

        finally:
            os.unlink(tmp)  # delete the temp file no matter what

        return file

    def clean_file(self):
        """Function that validates the file type, name and size"""
        file = self.cleaned_data['file']
        format_type = None
        file_category = None

        if self.is_disbursement:
            file_category = self.cleaned_data['file_category']
        else:
            format_type = self.cleaned_data['format']

        if file:
            # validate unique fields
            if format_type and not format_type.validate_collection_unique():
                raise forms.ValidationError(_("This Format doesn't contain the Collection unique fields"))

            self.validate_file_type_size_and_name(file)
            return self.write_file_to_disk(file, format_type, file_category)

    def save(self, commit=True):
        """Assign values to specific attributes before saving the doc object"""
        instance = super().save(commit=False)
        instance.owner = self.request.user
        instance.type_of = self.type_of
        instance.collection_data = self.collection

        if commit:
            instance.save()
        return instance


class FileCategoryForm(forms.ModelForm):
    """
    Form for FileCategory Model which define the format of uploaded disbursement documents
    """

    class Meta:
        model = FileCategory
        fields = "__all__"
        labels = {
            'unique_field': _("Mobile number header position. ex: A-1"),
            'amount_field': _("Amount header position. ex: B-1"),
            'issuer_field': _("Issuers header position. ex: C-1")
        }
        exclude = ["user_created"]

    def __init__(self, *args, request=None, **kwargs):
        """Handle initiating a file category form"""
        self.col_row_format = "must be in the form col-row or letter-number ex: A-1"
        self.three_headers = "Mobile number, Amount and Issuer option fields"
        self.two_headers = "Mobile number and Amount fields"
        self.is_normal_flow = False

        super().__init__(*args, **kwargs)
        self.fields['issuer_field'].required = True
        self.request = request

        # Handle updating existing file category
        if self.request is None and self.instance.pk is not None:
            if self.instance.user_created.root_entity_setups.is_normal_flow:
                self.fields.pop('issuer_field')
                self.is_normal_flow = True

        # Handle creating new file category
        if self.request is not None and self.request.user.root_entity_setups.is_normal_flow:
            self.fields.pop('issuer_field')
            self.is_normal_flow = True

    def clean_name(self):
        """Clean name field"""
        file_category_qs = FileCategory.objects.filter(
            Q(name=self.cleaned_data["name"]) &
            Q(user_created__hierarchy=self.request.user.hierarchy)
        )

        file_category = file_category_qs.first()

        # updating
        if self.instance:
            # not updating name -> ok
            if file_category_qs.exists() and file_category.id == self.instance.id:
                return self.cleaned_data["name"]
            # updating name but it arleady exist -> not ok
            if file_category_qs.exists() and file_category.id != self.instance.id:
                raise forms.ValidationError(self.add_error('name', _('This name already exist')))
            # updating name and it doesn't exist -> ok

        # creating
        elif file_category_qs.exists():
            raise forms.ValidationError(self.add_error('name', _('This name already exist')))

        return self.cleaned_data["name"]

    def clean_no_of_reviews_required(self):
        """Clean no_of_reviews_required field"""
        checkers_users_number = User.objects.get_all_checkers(self.request.user.hierarchy).count()
        no_of_reviews = self.cleaned_data['no_of_reviews_required']

        if no_of_reviews == 0:
            raise forms.ValidationError(_("Number of reviews must be greater than zero"))
        if no_of_reviews > checkers_users_number:
            raise forms.ValidationError(_("Number of reviews must be less than or equal the number of checkers"))
        return self.cleaned_data['no_of_reviews_required']

    def clean(self):
        """Clean file header fields"""
        unique_field = self.cleaned_data.get('unique_field')
        amount_field = self.cleaned_data.get('amount_field')
        issuer_field = self.cleaned_data.get('issuer_field')

        if not self.is_normal_flow:
            if not (unique_field and amount_field and issuer_field):
                return super().clean()
        elif self.is_normal_flow:
            if not (unique_field and amount_field):
                return super().clean()

        if not self.is_normal_flow and any('-' not in field for field in [unique_field, amount_field, issuer_field]):
            raise forms.ValidationError(_(f"{self.three_headers} {self.col_row_format}"))
        if self.is_normal_flow and any('-' not in field for field in [unique_field, amount_field]):
            raise forms.ValidationError(_(f"{self.two_headers} {self.col_row_format}"))

        col1, row1 = unique_field.split('-')
        col2, row2 = amount_field.split('-')
        col3, row3 = issuer_field.split('-') if issuer_field else ('', '')

        if self.is_normal_flow:
            if not all([col1.isalpha(), col2.isalpha(), row1.isnumeric(), row2.isnumeric()]):
                raise forms.ValidationError(_(f"{self.two_headers} {self.col_row_format}"))

            if row1 != row2:
                raise forms.ValidationError(_(f"{self.two_headers} must be on the same row"))
            elif col1 == col2:
                raise forms.ValidationError(_(f"{self.two_headers} can not be on the same column"))
        else:
            if not all([
                col1.isalpha(), col2.isalpha(), col3.isalpha(), row1.isnumeric(), row2.isnumeric(), row3.isnumeric()
            ]):
                raise forms.ValidationError(_(f"{self.three_headers} {self.col_row_format}"))
            if not (row1 == row2 == row3):
                raise forms.ValidationError(_(f"{self.three_headers} must be on the same row"))
            if col1 == col2 or col1 == col3 or col2 == col3:
                raise forms.ValidationError(_(f"{self.three_headers} can not be on the same column"))

        return self.cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.user_created = self.request.user.root
        if commit:
            instance.save()
        return instance


class DocReviewForm(forms.ModelForm):

    comment = forms.CharField(required=False)
    is_ok = forms.CharField()

    class Meta:
        model = DocReview
        fields = ['is_ok', 'comment']

    def clean_is_ok(self):
        if self.cleaned_data.get('is_ok') == '0':
            self.cleaned_data['is_ok'] = False
        else:
            self.cleaned_data['is_ok'] = True
        return self.cleaned_data['is_ok']

    def clean_comment(self):
        if not self.cleaned_data.get('is_ok') and not self.cleaned_data.get('comment'):
            raise forms.ValidationError(_('Rejection reason is required'))
        return self.cleaned_data.get('comment')


class OtpForm(forms.Form):

    otp_widget = forms.TextInput(attrs={'class': 'form-control', 'type': 'text', 'id': 'pin1'})
    pin1 = forms.CharField(
            max_length=6,
            label="",
            widget=otp_widget,
            strip=False,
            help_text=_('You will recieve a message on your phone within 30 seconds')
    )

    class Meta:
        fields = ['pin1']

    def clean_pin1(self):
        password = self.cleaned_data['pin1']
        if password == self.request.user.otp:
            return password
        else:
            raise forms.ValidationError(_('Code is not valid'))


class DownloadFilterForm(forms.Form):
    start_date = forms.DateField(
        input_formats=['%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d'],
        widget=forms.TextInput(
            attrs={
                'class': 'datepicker form-control date-download-form',
                'type': 'text',
                'style': 'width:125px;',
            }
        ),
        required=True
    )
    end_date = forms.DateField(
        input_formats=['%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d'],
        widget=forms.TextInput(
            attrs={
                'class': 'datepicker form-control date-download-form',
                'type': 'text',
                'style': 'width:125px;',
            }
        ),
        required=True
    )

    def clean(self):
        cleaned_data = super(DownloadFilterForm, self).clean()
        start_date = cleaned_data.get("start_date", None)
        end_date = cleaned_data.get("end_date", None)

        if start_date is None:
            self.add_error('start_date', _('Can\'t be blank'))
        if end_date is None:
            self.add_error('end_date', _('Can\'t be blank'))

        return cleaned_data


class FormatForm(forms.ModelForm):

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.request = request

    class Meta:
        model = Format
        fields = ['name'] + [f"identifier{num}" for num in range(1, 11)]
        exclude = ['category', 'num_of_identifiers', 'collection', 'hierarchy', 'data_type']

    def clean(self):
        data = self.cleaned_data.copy()
        del data['DELETE']
        ids = Format(**data).identifiers()
        if len(ids) < 2:
            raise forms.ValidationError('You need to add at least two headers')

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.hierarchy = self.request.user.hierarchy
        if commit:
            instance.save()
        return instance


class FileCategoryViewForm(forms.ModelForm):

    name = forms.ModelChoiceField(
            queryset=None,
            widget=forms.Select(
                    attrs={'class': 'form-control', 'style': 'height: 32px;/n' 'margin-top: 2px;'}
            ),
            label='File Category',
    )
    from_date = forms.CharField(
            widget=forms.TextInput(
                    attrs={'class': 'datepicker', 'type': 'text', 'size': '30', 'style': 'width:125px;'}
            ),
            required=False
    )
    to_date = forms.CharField(
            widget=forms.TextInput(
                    attrs={'class': 'datepicker', 'type': 'text', 'size': '30', 'style': 'width:125px;'}
            ),
            required=False
    )

    class Meta:
        model = FileCategory
        fields = ['name']

    def __init__(self):
        super(FileCategoryViewForm, self).__init__()
        self.fields["name"].queryset = FileCategory.objects.filter(
                Q(user_created__hierarchy=self.request.user.hierarchy)
        )


class CollectionDataForm(forms.ModelForm):

    class Meta:
        model = CollectionData
        fields = '__all__'
        exclude = ['user']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        collection_data = CollectionData.objects.filter(user__hierarchy=self.request.user.hierarchy).first()

        super().__init__(*args, instance=collection_data, ** kwargs)

        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.user = self.request.user
        if commit:
            instance.save()
        return instance


FormatFormSet = forms.modelformset_factory(
        model=Format, form=FormatForm, min_num=1, validate_min=True, can_delete=True, extra=0
)

FileCategoryFormSet = forms.modelformset_factory(
    model=FileCategory, form=FileCategoryForm, min_num=1, validate_min=True, can_delete=True, extra=0
)
