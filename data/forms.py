import datetime
import logging
import os
import tempfile

import xlrd
from django import forms
from django.core.validators import FileExtensionValidator
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from data.models import Doc, DocReview, FileCategory,CollectionData,Format
# TO BE SET IN settings.py
from data.utils import get_client_ip
from users.models import User

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
        if not self.cleaned_data.get('is_ok') and not self.cleaned_data.get('comment'):
            raise forms.ValidationError(_('Rejection reason is required'))
        return self.cleaned_data.get('comment')


class FileDocumentForm(forms.ModelForm):
    """
    A form for uploading files
    """

    file = forms.FileField(
        label=_('Select a file'),
        help_text=_('max. 42 megabytes'),
        validators=(FileExtensionValidator(allowed_extensions=[
                    'xls', 'xlsx', 'csv', 'txt', 'doc', 'docx']),)
    )

    def __init__(self,*args,**kwargs):
        self.request = kwargs.pop('request')
        self.is_disbursement = kwargs.pop('is_disbursement', False)
        self.collection = kwargs.pop('collection',None)
        super().__init__(*args, **kwargs)
        if self.is_disbursement:
            self.type_of = 1
            del self.fields['format']
        else:
            self.type_of = 2
            del self.fields['file_category']
        
    def clean_file(self):
        """
        Function that validates the file type, file name and size
        """
        file = self.cleaned_data['file']
        format_type = None
        category = None
        if self.type_of == 2:
            format_type = self.cleaned_data['format']
        else:
            category = self.cleaned_data['file_category']

        if file:
            # validate unique fields
            if format_type and not format_type.validate_collection_unique():
                raise forms.ValidationError(
                    _("This Format doesn't contain the Collection unique fields"))


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

                    if 'openxml' not in file_type:
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

                if format_type and format_type.num_of_identifiers != 0:
                    try:
                        xl_workbook = xlrd.open_workbook(tmp)
                    except Exception:
                        raise forms.ValidationError(
                            _('File uploaded in not in proper form'))
                    xl_sheet = xl_workbook.sheet_by_index(0)

                    if len(format_type.identifiers()) != xl_sheet.ncols:
                        raise forms.ValidationError(
                            _('File uploaded in not in proper form'))
                    # validate headers
                    cell_obj = next(xl_sheet.get_rows())
                    headers = [data.value for data in cell_obj]
                    if not format_type.headers_match(headers):
                        raise forms.ValidationError(
                            _("File headers doesn't match the format identifiers"))

                elif self.type_of == 1:
                    try:
                        xl_workbook = xlrd.open_workbook(tmp)
                    except Exception:
                        raise forms.ValidationError(
                            _('File uploaded in not in proper form'))
                    xl_sheet = xl_workbook.sheet_by_index(0)

                    if category.MIN_IDS_LENGTH > xl_sheet.ncols:                    
                        raise forms.ValidationError(
                            _('File uploaded in not in proper form'))

            finally:
                os.unlink(tmp)  # delete the temp file no matter what

        return file

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.owner = self.request.user
        instance.collection_data = self.collection
        instance.type_of = self.type_of

        if commit:
            instance.save()    
        return instance

    class Meta:
        model = Doc
        fields = [
            'file_category',
            'format',
            'file'
        ]


class CollectionDataForm(forms.ModelForm):
    class Meta:
        model = CollectionData
        fields = '__all__'
        exclude = ('user',)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        collection_data = CollectionData.objects.filter(
            user__hierarchy=self.request.user.hierarchy).first()
        
        super().__init__(*args, instance=collection_data, ** kwargs)

        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'


    def save(self,commit=True):
        instance = super().save(commit=False)
        instance.user = self.request.user
        if commit:
            instance.save()
        return instance

class FileCategoryForm(forms.ModelForm):
    amount_field = forms.CharField(label=_('amount header position'),
        widget=forms.TextInput(attrs={'placeholder': 'ex: A-1'}))
    unique_field = forms.CharField(label=_('msisdn header position'),
        widget=forms.TextInput(attrs={'placeholder': 'ex: B-1'}))
    class Meta:
        model = FileCategory
        fields = '__all__'
        exclude = ('user_created',)

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request

    def clean_name(self):
      
        file_category_qs = FileCategory.objects.filter(
            Q(name=self.cleaned_data["name"]) &
            Q(user_created__hierarchy=self.request.user.hierarchy))
        
        file_category = file_category_qs.first()
        
        # updating
        if self.instance:
            # not updating name -> ok
            if file_category_qs.exists() and file_category.id == self.instance.id:
                return self.cleaned_data["name"]
            # updating name but it arleady exist -> not ok
            if file_category_qs.exists() and file_category.id != self.instance.id:
                raise forms.ValidationError(self.add_error(
                    'name', _('this name already exist')))
            # updating name and it doesn't exist -> ok     

        # creating
        elif file_category_qs.exists():
            raise forms.ValidationError(self.add_error(
                'name', _('this name already exist')))

        return self.cleaned_data["name"]

    def clean_no_of_reviews_required(self):
        checkers_no = User.objects.get_all_checkers(
            self.request.user.hierarchy).count()
        if self.cleaned_data['no_of_reviews_required'] > checkers_no:
            raise forms.ValidationError(
                _('number of reviews must be less than or equal the number of checkers'))
        return self.cleaned_data['no_of_reviews_required']

    def clean(self):
        unique_field = self.cleaned_data.get('unique_field')
        amount_field = self.cleaned_data.get('amount_field')
        if '-' not in unique_field or '-' not in amount_field:
            raise forms.ValidationError(
                _("Msisdn and Amount fields must be in the following format col-row ex: A-1 "))
        col1, row1 = unique_field.split('-')
        col2, row2 = amount_field.split('-')
        if not col1.isalpha() or not col2.isalpha() or not row1.isnumeric() or not row2.isnumeric():
            raise forms.ValidationError(
                _("Msisdn and Amount fields must be in the form letter-number "))
        if row1 != row2:
            raise forms.ValidationError(_("Msisdn and Amount fields must be on the same row"))
        elif col1 == col2:
            raise forms.ValidationError(
                _("Msisdn and Amount fields can not be on the same column"))

        return self.cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.user_created = self.request.user.root
        if commit:
            instance.save()
        return instance


class FileCategoryViewForm(forms.ModelForm):
    name = forms.ModelChoiceField(queryset=None,
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
            'name'
        ]

    def __init__(self):
        super(FileCategoryViewForm, self).__init__()
        self.fields["name"].queryset = FileCategory.objects.filter(
            Q(user_created__hierarchy=self.request.user.hierarchy))


class OtpForm(forms.Form):
    otp_widget = forms.TextInput(
        attrs={'class': 'form-control', 'type': 'text', 'id': 'pin1'})
    pin1 = forms.CharField(max_length=6,
                           label="",
                           help_text=_('You will recieve a message on your phone within 30 seconds'),
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
        fields = ('name', 'identifier1', 'identifier2',
                  'identifier3', 'identifier4', 'identifier5', 
                  'identifier6', 'identifier7', 'identifier8',
                  'identifier9', 'identifier10')
        exclude = ('category', 'num_of_identifiers',
                   'collection', 'hierarchy', 'data_type')

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


FormatFormSet = forms.modelformset_factory(
    model=Format, form=FormatForm,
    min_num=1, validate_min=True, can_delete=True, extra=1)

FileCategoryFormSet = forms.modelformset_factory(
    model=FileCategory, form=FileCategoryForm,
    min_num=1, validate_min=True, can_delete=True, extra=1)
