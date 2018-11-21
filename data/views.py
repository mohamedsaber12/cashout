# Create your views here.
from __future__ import print_function, unicode_literals

import datetime
import json
import logging

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
from django.views.generic import ListView
from django.views.static import serve

from data.forms import DocReviewForm, DownloadFilterForm, FileDocumentForm
from data.models import Doc, DocReview, FileCategory
from data.tasks import handle_disbursement_file
from data.utils import get_client_ip, paginator
from users.decorators import setup_required
from users.models import User

UPLOAD_LOGGER = logging.getLogger("upload")
DELETED_FILES_LOGGER = logging.getLogger("deleted_files")
UNAUTHORIZED_UPLOAD_LOGGER = logging.getLogger("unauthorized_upload")
UNAUTHORIZED_FILE_DELETE_LOGGER = logging.getLogger("unauthorized_file_delete")
UPLOAD_ERROR_LOGGER = logging.getLogger("upload_error")
DOWNLOAD_LOGGER = logging.getLogger("download_serve")


@login_required
@setup_required
def file_upload(request):
    """
    Function that allows the logged in user from the can_upload group to upload
    a file. The file is later processed by the function 'handle_uploaded_file'.
    It handles the ajax calls for the OTP check too
    """
    FileDocumentForm.request = request
    docs = Doc.objects.select_related('owner').filter(
        Q(owner__hierarchy=request.user.hierarchy)
    )
    category = FileCategory.objects.get_by_hierarchy(request.user.hierarchy)
    has_file_category = bool(category)

    if request.method == 'POST' and request.user.is_maker and has_file_category:
        FileDocumentForm.category = category
        form_doc = FileDocumentForm(request.POST, request.FILES)

        if form_doc.is_valid():
            file_doc = Doc(owner=request.user,
                           file=request.FILES['file'],
                           file_category=category)
            file_doc.save()
            now = datetime.datetime.now()
            UPLOAD_LOGGER.debug(
                '%s uploaded file at ' % request.user + str(now))
            handle_disbursement_file.delay(file_doc.id)

            # Redirect to the document list after POST
            return HttpResponseRedirect(request.path)
        else:
            UPLOAD_ERROR_LOGGER.debug(
                'UPLOAD ERROR: %s by %s at %s from IP Address %s' % (
                    form_doc.errors, request.user,
                    datetime.datetime.now(), get_client_ip(request)))

            return JsonResponse(form_doc.errors, status=400)

    else:
        form_doc = None
        files = files_based_on_group_of_logged_in_user(request, docs)
        if isinstance(files, QuerySet):
            try:
                docs = paginator(request, files)
            except:
                docs = paginator(request, '')
        else:
            docs = files

    context = {'docs': docs,
               'form_doc': form_doc,
               'has_file_category': has_file_category
               }

    return render(request, 'data/index.html', context=context)


# TODO: Customize permissions based on file types permissions
def files_based_on_group_of_logged_in_user(request, docs):
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


@setup_required
@login_required
@permission_required('data.delete_file')
def file_delete(request, pk, template_name='data/file_confirm_delete.html'):
    """
    Function that deletes a file
    """
    file_obj = get_object_or_404(Doc, pk=pk)
    if request.method == 'POST':
        if request.user.has_perm('data.delete_file'):
            file_obj.delete()
            now = datetime.datetime.now()
            DELETED_FILES_LOGGER.debug(
                '%s deleted a file at %s with IP Address %s' % (
                    request.user, now, get_client_ip(request)))
            return redirect('data:main_view')
        else:
            UNAUTHORIZED_FILE_DELETE_LOGGER.debug(
                "Unauthorized file delete %s id %s at %s IP Address %s" % (
                    request.user, request.user.id,
                    str(datetime.datetime.now()), get_client_ip(request)))
            messages.add_message(request, messages.INFO,
                                 "You are not authorized to delete a file")
            return redirect('data:main_view')
    return render(request, template_name, {'object': file_obj})



def page_not_found_view(request):
    return render(request, 'data/404.html', status=404)


def error_view(request):
    return render(request, 'data/500.html', status=500)


def permission_denied_view(request):
    return render(request, 'data/403.html', status=403)


def bad_request_view(request):
    return render(request, 'data/400.html', status=400)


@login_required
def document_view(request, doc_id):
    template_name = 'data/document_viewer.html'
    doc = get_object_or_404(Doc, id=doc_id)
    review_form_errors = None
    reviews = None
    # True if user already reviewed this doc
    user_review_exist = None
    can_user_disburse = {}
    if doc.owner.hierarchy == request.user.hierarchy:
        if doc.is_disbursed:
            return redirect(reverse("disbursement:disbursed_data", args=(doc_id,)))
        if request.user.is_checker:
            if not doc.can_be_disbursed:
                raise Http404

            reviews = DocReview.objects.filter(doc=doc)
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
        messages.warning(request, "This document doesn't exist")
        return redirect(reverse("data:main_view"))

    context = {
        'doc': doc,
        'review_form_errors': review_form_errors,
        'reviews': reviews,
        'user_review_exist': user_review_exist,
        'can_user_disburse': can_user_disburse
    }
    if bool(request.GET.dict()):
        context['redirect'] = 'true'
        context.update(request.GET.dict())
    else:
        context['redirect'] = 'false'

    return render(request, template_name=template_name, context=context)


@setup_required
@login_required
def protected_serve(request, path, document_root=None, show_indexes=False):
    DOWNLOAD_LOGGER.debug(
        get_client_ip(request) + ' downloaded ' + path + 'at' + str(datetime.datetime.now()) + ' ' + str(request.user))
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


class DocumentDetailsListView(LoginRequiredMixin, ListView):
    model = Doc
    template_name = 'data/document_details_list.html'

    def get_queryset(self):
        return super().get_queryset().filter(
            owner__hierarchy=self.request.user.hierarchy)
