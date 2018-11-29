import datetime
import logging
import os
import tempfile

import xlrd
from django import forms
from django.core.validators import FileExtensionValidator
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from data.models import Doc, DocReview, FileCategory
# TO BE SET IN settings.py
from data.utils import get_client_ip

UPLOAD_LOGGER = logging.getLogger("upload")

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
MIME_UPLOAD_FILE_TYPES = [
    'plain',
    'octet-stream']

TASK_UPLOAD_FILE_MAX_SIZE = 5242880
UNICODE = set(';:></*%$.\\')


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
        print('clean_comment', self.cleaned_data.get(
            'is_ok'), self.cleaned_data.get('comment'))
        if not self.cleaned_data.get('is_ok') and not self.cleaned_data.get('comment'):
            raise forms.ValidationError('comment field is required')
        return self.cleaned_data.get('comment')


class FileDocumentForm(forms.ModelForm):
    """
    A form for uploading files
    """

    file = forms.FileField(
        label=_('Select a file'),
        help_text='max. 42 megabytes',
        validators=(FileExtensionValidator(allowed_extensions=[
                    'xls', 'xlsx', 'csv', 'txt', 'doc', 'docx']),)
    )

    def clean_file(self):
        """
        Function that validates the file type, file name and size
        """
        file = self.cleaned_data['file']
        file_category = self.category
        if file:

            file_type = file.content_type.split('/')[1]
            number_of_dots = len(file.name.split('.'))
            if number_of_dots != 2:
                raise forms.ValidationError(
                    _('File type is not supported'))
            try:
                filename = "".join(file.name.split('.')[:-1])
            except ValueError:
                raise forms.ValidationError(
                    _('File name is not proper'))
            if not any((c in UNICODE) for c in filename):
                if file_type in TASK_UPLOAD_FILE_TYPES:
                    if file.size > TASK_UPLOAD_FILE_MAX_SIZE:
                        raise forms.ValidationError(
                            '%s' % _('Please keep file size under 5242880'))
                    if len(file.name.split('.')[0]) > 100:
                        raise forms.ValidationError(
                            _('Filename must be less than 255 characters'))

                    if 'openxml' not in file_type and file_category.is_processed:
                        UPLOAD_LOGGER.debug('UPLOAD ERROR: file_type not supported %s by %s at %s from IP Address %s' % (
                            str(file_type),
                            str(self.request.user.username),
                            datetime.datetime.now(), get_client_ip(self.request)))
                        raise forms.ValidationError(
                            _('File type is not supported'))
                else:
                    UPLOAD_LOGGER.debug('UPLOAD ERROR: file_type not supported %s by %s at %s from IP Address %s' % (
                        str(file_type),
                        str(self.request.user.username),
                        datetime.datetime.now(), get_client_ip(self.request)))
                    raise forms.ValidationError(
                        _('File type is not supported'))
            else:
                raise forms.ValidationError(
                    _('Filename should not include any unicode characters ex: :, >, <, \, /, $, * '))
            try:
                fd, tmp = tempfile.mkstemp()
                with os.fdopen(fd, 'wb') as out:
                    out.write(file.read())

                if file_category.num_of_identifiers != 0 and file_category.processed:
                    try:
                        xl_workbook = xlrd.open_workbook(tmp)
                    except Exception:
                        raise forms.ValidationError(
                            _('File uploaded in not in proper form'))
                    xl_sheet = xl_workbook.sheet_by_index(0)

                    if len(file_category.identifiers()) != xl_sheet.ncols:
                        raise forms.ValidationError(
                            _('File uploaded in not in proper form'))
            finally:
                os.unlink(tmp)  # delete the temp file no matter what

        return file

    def save(self, commit=True):
        m = super(FileDocumentForm, self).save(commit=commit)
        self.instance.owner = self.request.user
        return m

    class Meta:
        model = Doc
        fields = [
            'file',
        ]


class FileCategoryForm(forms.ModelForm):
    class Meta:
        model = FileCategory
        fields = '__all__'
        exclude = ('user_created',
                   'num_of_identifiers', 'is_processed')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name == 'has_header':
                field.widget.attrs['class'] = 'js-switch'
                pass
            else:
                field.widget.attrs['class'] = 'form-control'

    def clean_file_type(self):
        try:
            file_category = FileCategory.objects.get(Q(file_type=self.cleaned_data["file_type"]) &
                                                     Q(user_created__hierarchy=self.request.user.hierarchy))
        except:
            file_category = None

        try:
            if not file_category == self.obj and self.cleaned_data["file_type"] == file_category.file_type:
                raise forms.ValidationError(self.add_error(
                    'file_type', 'Name already Exist'))
            else:
                return self.cleaned_data["file_type"]
        except AttributeError:
            return self.cleaned_data["file_type"]


class FileCategoryViewForm(forms.ModelForm):
    file_type = forms.ModelChoiceField(queryset=None,
                                       widget=forms.Select(attrs={'class': 'form-control',
                                                                  'style': 'height: 32px;/n'
                                                                           'margin-top: 2px;'}),
                                       label='File Category', )
    from_date = forms.CharField(widget=forms.TextInput(attrs={'class': 'datepicker',
                                                              'type': 'text',
                                                              'size': '30',
                                                              'style': 'width:125px;'
                                                              }), required=False)
    to_date = forms.CharField(widget=forms.TextInput(attrs={'class': 'datepicker',
                                                            'type': 'text',
                                                            'size': '30',
                                                            'style': 'width:125px;'
                                                            }), required=False)

    class Meta:
        model = FileCategory
        fields = [
            'file_type'
        ]

    def __init__(self):
        super(FileCategoryViewForm, self).__init__()
        self.fields["file_type"].queryset = FileCategory.objects.filter(
            Q(user_created__hierarchy=self.request.user.hierarchy))


class OtpForm(forms.Form):
    otp_widget = forms.TextInput(
        attrs={'class': 'form-control', 'type': 'text', 'id': 'pin1'})
    pin1 = forms.CharField(max_length=6,
                           label="",
                           help_text='You will recieve a message on your phone within 30 seconds',
                           widget=otp_widget,
                           strip=False,
                           )

    class Meta:
        fields = ('pin1',)

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
            self.add_error('start_date', 'Can\'t be blank')
        if end_date is None:
            self.add_error('end_date', 'Can\'t be blank')

        return cleaned_data
