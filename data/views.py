# Create your views here.
from __future__ import print_function, unicode_literals

import datetime
import json
import logging
import xlrd
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.db.models.query import QuerySet
from django.http import (Http404, HttpResponse, HttpResponseRedirect,
                         JsonResponse)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.generic import ListView, DetailView,View
from django.views.static import serve

from data.forms import DocReviewForm, DownloadFilterForm, FileDocumentForm,FormatFormSet,FileCategoryFormSet
from data.models import Doc, DocReview, FileCategory, Format,CollectionData
from data.tasks import handle_disbursement_file, handle_uploaded_file
from data.utils import get_client_ip, paginator
from users.decorators import (setup_required, root_or_maker_or_uploader, 
                              collection_users, disbursement_users)
from users.models import User

UPLOAD_LOGGER = logging.getLogger("upload")
DELETED_FILES_LOGGER = logging.getLogger("deleted_files")
UNAUTHORIZED_FILE_DELETE_LOGGER = logging.getLogger("unauthorized_file_delete")
UPLOAD_ERROR_LOGGER = logging.getLogger("upload_error")
DOWNLOAD_LOGGER = logging.getLogger("download_serve")
VIEW_DOCUMENT_LOGGER = logging.getLogger("view_document")


@login_required
@setup_required
def file_upload(request):
    """
    POST:
    View that allows the maker with a file category to upload a disbursement file.
    The file is later processed by the task 'handle_disbursement_file'.
    GET:
    View that list all documents related to logged in user hierarchy.
    Documents can be filtered by date.
    Documents are paginated ("docs_paginated") but not used in template.
    """
    format_qs = None
    doc_list_collection = None
    doc_list_disbursement = None
    can_upload = False
    user_has_upload_perm = False
    status = request.user.get_status(request)
    if status == 'disbursement':
        format_qs = FileCategory.objects.get_by_hierarchy(
            request.user.hierarchy)
        can_upload = format_qs.exists()
        user_has_upload_perm = request.user.is_maker or request.user.is_upmaker
        if request.method == 'POST' and can_upload and user_has_upload_perm and request.user.root.client.is_active:
            form_doc = FileDocumentForm(
                request.POST, request.FILES, request=request, is_disbursement=True)

            if form_doc.is_valid():
                file_doc = form_doc.save()
                now = datetime.datetime.now()
                UPLOAD_LOGGER.debug(
                    '%s uploaded disbursement file at ' % request.user + str(now))
             
                handle_disbursement_file.delay(file_doc.id)

                # Redirect to the document list after POST
                return HttpResponseRedirect(request.path)
            else:
                UPLOAD_ERROR_LOGGER.debug(
                    'Disbursement UPLOAD ERROR: %s by %s at %s from IP Address %s' % (
                        form_doc.errors, request.user,
                        datetime.datetime.now(), get_client_ip(request)))

                return JsonResponse(form_doc.errors, status=400)

        doc_list_disbursement = Doc.objects.filter(
            owner__hierarchy=request.user.hierarchy,
            type_of=Doc.DISBURSEMENT)
        doc_list_disbursement = filter_docs_by_date(
            request, doc_list_disbursement)
    else:
        format_qs = Format.objects.filter(hierarchy=request.user.hierarchy)
        collection = CollectionData.objects.filter(
            user__hierarchy=request.user.hierarchy).first()
        can_upload = bool(collection)
        user_has_upload_perm = request.user.is_uploader or request.user.is_upmaker
        if (request.method == 'POST' and can_upload and user_has_upload_perm and request.user.root.client.is_active):
            form_doc = FileDocumentForm(
                request.POST, request.FILES,request=request, collection=collection)

            if form_doc.is_valid():
                file_doc = form_doc.save()
                now = datetime.datetime.now()
                UPLOAD_LOGGER.debug(
                    '%s uploaded collection file at ' % request.user + str(now))           
                handle_uploaded_file.delay(file_doc.id)                

                # Redirect to the document list after POST
                return HttpResponseRedirect(request.path)
            else:
                UPLOAD_ERROR_LOGGER.debug(
                    'Collection UPLOAD ERROR: %s by %s at %s from IP Address %s' % (
                        form_doc.errors, request.user,
                        datetime.datetime.now(), get_client_ip(request)))

                return JsonResponse(form_doc.errors, status=400)
        
        doc_list_collection = Doc.objects.filter(
            owner__hierarchy=request.user.hierarchy,
            type_of=Doc.COLLECTION)
        doc_list_collection = filter_docs_by_date(
            request, doc_list_collection)
    
   
    context = {
        'doc_list_disbursement': doc_list_disbursement,
        'doc_list_collection': doc_list_collection,
        'format_qs': format_qs,
        'can_upload':can_upload,
        'user_has_upload_perm': user_has_upload_perm,
        'status': status
    }

    return render(request, 'data/index.html', context=context)


def filter_docs_by_date(request, docs):
    """
    Function to return the document files based of date
    :param request:
    :param docs:
    :return:
    """
    if not (request.GET.get('from_date') and request.GET.get('to_date')):
        return docs
    else:
        docs = docs.filter(
            created_at__range=(request.GET.get('from_date', ''),
                               request.GET.get('to_date', ''))
        )

    return docs


## this view is not used ##
@setup_required
@login_required
def check_download_xlsx(request):
    if request.is_ajax():
        pk = request.GET.get("doc_id")
        doc = Doc.objects.get(id=pk)
        result = {}

        if doc.is_downloaded:
            result.update(check=False)
        else:
            result.update(check=True)

        return HttpResponse(json.dumps(result), content_type='application/json')
    else:
        return HttpResponse("Wrong request")

## this view is not used ##
@setup_required
@login_required
def download_excel_with_trx_temp_view(request):
    """
    View Handling and validating the form only then send the filter parameters to
    ajax response to trigger the url of the excel download
    :param request:
    :return:
    """
    if request.method == 'POST':
        form = DownloadFilterForm(request.POST)
        if form.is_valid():
            start_date = request.POST.get('start_date', None)
            end_date = request.POST.get('end_date', None)
            file_category = get_object_or_404(
                FileCategory, user_created=request.user)
            url = reverse('download_xls', kwargs={
                "start_date": start_date,
                "end_date": end_date,
                "file_category_id": file_category.id
            })

            return HttpResponse(
                content_type="application/json",
                content=json.dumps({"url": url})
            )

        else:
            return HttpResponse(content_type="application/json", content=form.errors)
    else:
        raise Http404


@method_decorator([setup_required, login_required], name='dispatch')
class FileDeleteView(View):
    """
    Function that deletes a file
    """

    def post(self, request,pk=None, *args, **kwargs):
        if not request.is_ajax():
            return JsonResponse(data={}, status=403)
            
        file_obj = get_object_or_404(Doc, pk=pk)
        file_obj.delete()
        now = datetime.datetime.now()
        DELETED_FILES_LOGGER.debug(
            '%s deleted a file at %s with IP Address %s' % (
                request.user, now, get_client_ip(request)))
        return JsonResponse(data={},status=200)
        
        # case user has no permission
        # UNAUTHORIZED_FILE_DELETE_LOGGER.debug(
        #     "Unauthorized file delete %s id %s at %s IP Address %s" % (
        #         request.user, request.user.id,
        #         str(datetime.datetime.now()), get_client_ip(request)))

@disbursement_users
@login_required
def document_view(request, doc_id):
    """
    View document given doc_id.
    List checkers reviews.
    Checkers can review document.
    """
    template_name = 'data/document_viewer_disbursement.html'
    doc = get_object_or_404(Doc, id=doc_id)
    review_form_errors = None
    reviews = None
    # True if checker already reviewed this doc
    user_review_exist = None
    can_user_disburse = {}
    if doc.owner.hierarchy == request.user.hierarchy:
        # doc already dibursed
        if doc.is_disbursed:
            return redirect(reverse("disbursement:disbursed_data", args=(doc_id,)))
        if request.user.is_checker:
            # makers must notify checkers and allow the document to be dibursed
            # checker should not have access to doc url or id before that
            if not doc.can_be_disbursed:
                VIEW_DOCUMENT_LOGGER.debug(
                    f'Document doc_id {doc_id} can not be disbursed, checker {request.user.username}')
                raise Http404

            reviews = DocReview.objects.filter(doc=doc)
            #check if checker already reviewed this doc
            user_review_exist = DocReview.objects.filter(
                doc=doc, user_created=request.user).exists()

            if request.method == "POST" and not user_review_exist:

                doc_review_form = DocReviewForm(request.POST)
                if doc_review_form.is_valid():
                    doc_review_obj = doc_review_form.save(commit=False)
                    doc_review_obj.user_created = request.user
                    doc_review_obj.doc = doc
                    doc_review_obj.save()
                    user_review_exist = True
                else:
                    review_form_errors = doc_review_form.errors

            can_user_disburse = doc.can_user_disburse(request.user)
            can_user_disburse = {
                'can_disburse': can_user_disburse[0],
                'reason': can_user_disburse[1],
                'code': can_user_disburse[2]
            }

    else:
        VIEW_DOCUMENT_LOGGER.debug(
            f"""user viewing document from other hierarchy, 
            user: {request.user.username},user hierarchy: {request.user.hierarchy}, 
            doc hierarchy: {doc.owner.hierarchy} """)
        return redirect(reverse("data:main_view"))

    xl_workbook = xlrd.open_workbook(doc.file.path)
    xl_sheet = xl_workbook.sheet_by_index(0)
    excel_data = []
    for row in xl_sheet.get_rows():
        row_data = []
        for x, data in enumerate(row):
            row_data.append(data.value)
        excel_data.append(row_data)
            
    context = {
        'doc': doc,
        'review_form_errors': review_form_errors,
        'reviews': reviews,
        'user_review_exist': user_review_exist,
        'can_user_disburse': can_user_disburse,
        'excel_data': excel_data
    }
    if bool(request.GET.dict()):
        context['redirect'] = 'true'
        context.update(request.GET.dict())
    else:
        context['redirect'] = 'false'

    VIEW_DOCUMENT_LOGGER.debug(
        f'user: {request.user.username} viewed doc_id:{doc_id} ')
    return render(request, template_name=template_name, context=context)


@setup_required
@login_required
def protected_serve(request, path, document_root=None, show_indexes=False):
    DOWNLOAD_LOGGER.debug(
        get_client_ip(request) + ' downloaded ' + path + 'at' + str(datetime.datetime.now()) + ' ' + str(request.user))
    path = 'documents/' + path
    try:
        doc = Doc.objects.get(file=path)
        if doc.owner.hierarchy == request.user.hierarchy:
            return serve(request, path, document_root, show_indexes)
        else:
            return redirect('data:main_view')
    except Doc.DoesNotExist:
        return serve(request, path, document_root, show_indexes)
    except Doc.MultipleObjectsReturned:
        return redirect('data:main_view')


@setup_required
@login_required
def doc_download(request, doc_id):
    """
    Downloads Excel file that user had uploaded before.
    :param request: HttpRequest that handles user details.
    :param doc_id: Document's id to be fetched.
    :return: Downloadable excel or 404.
    """
    doc = Doc.objects.get(id=doc_id)
    if doc.owner.hierarchy == request.user.hierarchy:
        try:
            response = HttpResponse(
                doc.file, content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = 'attachment; filename=%s' % doc.filename()
            response['X-Accel-Redirect'] = '/media/' + doc.file.name
            DOWNLOAD_LOGGER.debug(
                f'user {request.user.username} downloaded doc_id: {doc_id} at {str(datetime.datetime.now())}')
        except Exception:
            DOWNLOAD_LOGGER.debug(
                'user: {0} tried to download doc_id: {1} but 404 was raised.'.format(
                    request.user.username,
                    doc_id
                )
            )
            raise Http404
        return response
    else:
        raise Http404


@method_decorator([setup_required, login_required, root_or_maker_or_uploader], name='dispatch')
class FormatListView(ListView):

    template_name = "data/formats.html"
    context_object_name = "format_qs"

    def get_queryset(self):
        if self.request.user.get_status(self.request) == 'collection':
            return Format.objects.filter(hierarchy=self.request.user.hierarchy)
        else:
            return FileCategory.objects.get_by_hierarchy(self.request.user.hierarchy)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        if self.request.user.get_status(self.request) == 'collection':
            context['formatform'] = FormatFormSet(
                queryset=context['format_qs'],
                prefix='format'
            )
            if not self.request.user.is_root:
                context['formatform'].can_delete = False
                context['formatform'].extra = 0
        else:
            context['formatform'] = FileCategoryFormSet(
                queryset=context['format_qs'],
                prefix='category'
            )
            
            if not self.request.user.is_root:
                context['formatform'].can_delete = False
                context['formatform'].extra = 0

        
        return context

    def post(self, request, *args, **kwargs):
        if self.request.user.get_status(self.request) == 'collection':
            form = FormatFormSet(
                request.POST,
                prefix='format',
                form_kwargs={'request': request}
            )
        else:
            form = FileCategoryFormSet(
                request.POST,
                prefix='category',
                form_kwargs={'request': request}
            )
        if form and form.is_valid():

            objs = form.save(commit=False)

            for obj in form.deleted_objects:
                obj.delete()

            for obj in objs:
                obj.save()

            return HttpResponse(content=json.dumps({"valid": True}), content_type="application/json")

        return HttpResponse(content=json.dumps({
            "valid": False,
            "reason": "validation",
            "errors": form.errors,
            "non_form_errors": form.non_form_errors()
        }), content_type="application/json")


@method_decorator([setup_required, login_required, collection_users], name='dispatch')
class RetrieveCollectionData(DetailView):
    http_method_names = ['get']
    template_name = "data/document_viewer_collection.html"

    def get_queryset(self,*args,**kwargs):
        return Doc.objects.filter(id=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doc_obj = context['object']
        xl_workbook = xlrd.open_workbook(doc_obj.file.path)
        xl_sheet = xl_workbook.sheet_by_index(0)

        excl_data = []
        for row in xl_sheet.get_rows():
            row_data = []
            for x, data in enumerate(row):
                row_data.append(data.value)
            excl_data.append(row_data)
        
        
        context['excel_data'] = excl_data
        return context
    
