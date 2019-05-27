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
from django.utils import translation
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.generic import ListView, DetailView,View
from django.views.static import serve
from django.views.decorators.http import require_safe

from data.forms import DocReviewForm, DownloadFilterForm, FileDocumentForm,FormatFormSet,FileCategoryFormSet
from data.models import Doc, DocReview, FileCategory, Format,CollectionData
from data.tasks import (handle_disbursement_file, handle_uploaded_file, notify_checkers, 
doc_review_maker_mail)
from data.utils import get_client_ip, paginator
from users.decorators import (setup_required, root_or_maker_or_uploader, 
                              collection_users, disbursement_users, root_only)
from users.models import User 

UPLOAD_LOGGER = logging.getLogger("upload")
DELETED_FILES_LOGGER = logging.getLogger("deleted_files")
UNAUTHORIZED_FILE_DELETE_LOGGER = logging.getLogger("unauthorized_file_delete")
UPLOAD_ERROR_LOGGER = logging.getLogger("upload_error")
DOWNLOAD_LOGGER = logging.getLogger("download_serve")
VIEW_DOCUMENT_LOGGER = logging.getLogger("view_document")


@require_safe
@login_required
@setup_required
def redirect_home(request):
    status = request.user.get_status(request)
    return redirect(f'data:{status}_home')

@login_required
@setup_required
@disbursement_users
def disbursement_home(request):
    """
    POST:
    View that allows the maker with a file category to upload a disbursement file.
    The file is later processed by the task 'handle_disbursement_file'.
    GET:
    View that list all documents related to logged in user hierarchy.
    Documents can be filtered by date.
    Documents are paginated ("docs_paginated") but not used in template.
    """
    format_qs = FileCategory.objects.get_by_hierarchy(
        request.user.hierarchy)
    can_upload = bool(format_qs)
    user_has_upload_perm = request.user.is_maker or request.user.is_upmaker
    if request.method == 'POST' and can_upload and user_has_upload_perm and request.user.root.client.is_active:
        form_doc = FileDocumentForm(
            request.POST, request.FILES, request=request, is_disbursement=True)

        if form_doc.is_valid():
            file_doc = form_doc.save()
            now = datetime.datetime.now()
            UPLOAD_LOGGER.debug(
                '%s uploaded disbursement file at ' % request.user + str(now))

            handle_disbursement_file.delay(
                file_doc.id, language=translation.get_language())

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
    
    context = {
        'doc_list_disbursement': doc_list_disbursement,
        'format_qs': format_qs,
        'can_upload': can_upload,
        'user_has_upload_perm': user_has_upload_perm,
    }

    return render(request, 'data/disbursement_home.html', context=context)

@login_required
@setup_required
@collection_users
def collection_home(request):
    """
    POST:
    View that allows the maker with a file category to upload a disbursement file.
    The file is later processed by the task 'handle_disbursement_file'.
    GET:
    View that list all documents related to logged in user hierarchy.
    Documents can be filtered by date.
    Documents are paginated ("docs_paginated") but not used in template.
    """
    format_qs = Format.objects.filter(hierarchy=request.user.hierarchy)
    collection = CollectionData.objects.filter(
        user__hierarchy=request.user.hierarchy).first()
    can_upload = bool(collection)
    user_has_upload_perm = request.user.is_uploader or request.user.is_upmaker
    if (request.method == 'POST' and can_upload and user_has_upload_perm and request.user.root.client.is_active):
        form_doc = FileDocumentForm(
            request.POST, request.FILES, request=request, collection=collection)

        if form_doc.is_valid():
            file_doc = form_doc.save()
            now = datetime.datetime.now()
            UPLOAD_LOGGER.debug(
                '%s uploaded collection file at ' % request.user + str(now))
            handle_uploaded_file.delay(
                file_doc.id, language=translation.get_language())

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


    context = {
        'doc_list_collection': doc_list_collection,
        'format_qs': format_qs,
        'can_upload': can_upload,
        'user_has_upload_perm': user_has_upload_perm,
    }

    return render(request, 'data/collection_home.html', context=context)


@method_decorator([root_only, setup_required, login_required], name='dispatch')
class FileDeleteView(View):
    """
    Function that deletes a file
    """

    def post(self, request,pk=None, *args, **kwargs):
        if not request.is_ajax():
            return JsonResponse(data={}, status=403)
    
        file_obj = get_object_or_404(
            Doc, pk=pk, owner__hierarchy=request.user.hierarchy)
        file_obj.delete()
        now = datetime.datetime.now()
        DELETED_FILES_LOGGER.debug(
            '%s deleted a file at %s with IP Address %s' % (
                request.user, now, get_client_ip(request)))
        return JsonResponse(data={},status=200)


@login_required
@disbursement_users
def document_view(request, doc_id):
    """
    related to disbursement
    View document given doc_id.
    List checkers reviews.
    Checkers can review document.
    """
    template_name = 'data/document_viewer_disbursement.html'
    doc = get_object_or_404(Doc, id=doc_id)
    review_form_errors = None
    reviews = None
    # True if checker already reviewed this doc or reviews are completed
    hide_review_form = True
    can_user_disburse = {}
    if doc.owner.hierarchy == request.user.hierarchy:
        # doc already dibursed
        if (
                doc.is_disbursed and 
                (
                    doc.owner == request.user or
                    request.user.is_checker or
                    request.user.is_root
                )
            ):
            return redirect(reverse("disbursement:disbursed_data", args=(doc_id,)))
        if request.user.is_checker:
            # makers must notify checkers and allow the document to be dibursed
            # checker should not have access to doc url or id before that
            if not doc.can_be_disbursed:
                VIEW_DOCUMENT_LOGGER.debug(
                    f'Document doc_id {doc_id} can not be disbursed, checker {request.user.username}')
                raise Http404
            
            if not doc.is_reviews_completed():
                if doc.is_reviews_rejected():
                    hide_review_form = True
                else:
                    # user_can_review: if can't then can't view the doc
                    # user_review_exist: checks if checker already reviewed this doc
                    user_can_review, user_review_exist = doc.can_user_review(request.user)
                    if not user_can_review and not user_review_exist:
                        raise Http404
                    # user can review then user review doesn't exist then show review form
                    hide_review_form = user_review_exist

            reviews = DocReview.objects.filter(doc=doc)

            if request.method == "POST" and not hide_review_form:

                doc_review_form = DocReviewForm(request.POST)
                
                if doc_review_form.is_valid():
                    doc_review_obj = doc_review_form.save(commit=False)
                    doc_review_obj.user_created = request.user
                    doc_review_obj.doc = doc
                    doc_review_obj.save()
                    # notify checkers of next level if review is ok and
                    # no checkers of the same current level already notified them
                    checkers_already_notified = reviews.filter(
                        user_created__level=request.user.level).exclude(
                        id=doc_review_obj.id).exists()
                    if doc_review_obj.is_ok and not checkers_already_notified:
                        notify_checkers.delay(
                            doc.id, request.user.level.level_of_authority+1, language=translation.get_language())
                    # notify the maker either way
                    doc_review_maker_mail.delay(
                        doc.id, doc_review_obj.id, language=translation.get_language())
                    hide_review_form = True
                else:
                    review_form_errors = doc_review_form.errors['comment'][0]

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
        return redirect(reverse("data:disbursement_home"))

    doc_data = None
    if doc.is_processed:
        doc_data = doc.disbursement_data.all()
    
    context = {
        'doc': doc,
        'review_form_errors': review_form_errors,
        'reviews': reviews,
        'hide_review_form': hide_review_form,
        'can_user_disburse': can_user_disburse,
        'doc_data': doc_data
    }
    if bool(request.GET.dict()):
        context['redirect'] = 'true'
        context.update(request.GET.dict())
    else:
        context['redirect'] = 'false'

    VIEW_DOCUMENT_LOGGER.debug(
        f'user: {request.user.username} viewed doc_id:{doc_id} ')
    return render(request, template_name=template_name, context=context)


@login_required
@setup_required
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


@login_required
@setup_required
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


@method_decorator([root_or_maker_or_uploader, setup_required, login_required], name='dispatch')
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


@method_decorator([collection_users, setup_required, login_required], name='dispatch')
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
    
