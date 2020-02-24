# Create your views here.
from __future__ import print_function, unicode_literals

import logging

import xlrd

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import (Http404, HttpResponse, HttpResponseRedirect, JsonResponse)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import translation
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_safe
from django.views.generic import DetailView, TemplateView, View
from django.views.static import serve

from users.decorators import (collection_users, disbursement_users, root_only,
                              root_or_maker_or_uploader, setup_required)
from users.models import CheckerUser, Levels

from .forms import (DocReviewForm, FileCategoryFormSet, FileDocumentForm, FormatFormSet)
from .models import CollectionData, Doc, DocReview, FileCategory, Format
from .tasks import (doc_review_maker_mail, handle_disbursement_file,
                    handle_uploaded_file, notify_checkers, notify_disbursers)
from .utils import get_client_ip


UPLOAD_LOGGER = logging.getLogger("upload")
UPLOAD_ERROR_LOGGER = logging.getLogger("upload_error")
DELETED_FILES_LOGGER = logging.getLogger("deleted_files")
UNAUTHORIZED_FILE_DELETE_LOGGER = logging.getLogger("unauthorized_file_delete")
DOWNLOAD_LOGGER = logging.getLogger("download_serve")
VIEW_DOCUMENT_LOGGER = logging.getLogger("view_document")


@require_safe
@login_required
@setup_required
def redirect_home(request):
    if request.user.is_superuser:
        return redirect(reverse('admin:index'))
    if request.user.is_instantapiviewer:
        return redirect(reverse('users:instant_transactions'))
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
    format_qs = FileCategory.objects.get_by_hierarchy(request.user.hierarchy)
    can_upload = bool(format_qs)
    user_has_upload_perm = request.user.is_maker or request.user.is_upmaker

    if request.method == 'POST' and can_upload and user_has_upload_perm and request.user.root.client.is_active:
        form_doc = FileDocumentForm(request.POST, request.FILES, request=request, is_disbursement=True)

        if form_doc.is_valid():
            file_doc = form_doc.save()
            UPLOAD_LOGGER.debug(f"""[DISBURSEMENT FILE UPLOAD]
            User: {request.user.username} from IP Address {get_client_ip(request)}
            Uploaded disbursement file with doc_id: {file_doc.id}""")
            handle_disbursement_file.delay(file_doc.id, language=translation.get_language())
            return HttpResponseRedirect(request.path)           # Redirect to the document list after POST
        else:
            UPLOAD_ERROR_LOGGER.debug(f"""[DISBURSEMENT FILE UPLOAD ERROR]
            Disbursement upload error: {form_doc.errors['file'][0]}
            By User: {request.user.username} from IP Address {get_client_ip(request)}""")
            return JsonResponse(form_doc.errors, status=400)

    doc_list_disbursement = Doc.objects.filter(owner__hierarchy=request.user.hierarchy, type_of=Doc.DISBURSEMENT)
    paginator = Paginator(doc_list_disbursement, 10)
    page = request.GET.get('page')
    docs = paginator.get_page(page)
    context = {
        'doc_list_disbursement': docs,
        'format_qs': format_qs,
        'can_upload': can_upload,
        'user_has_upload_perm': user_has_upload_perm
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
    collection = CollectionData.objects.filter(user__hierarchy=request.user.hierarchy).first()
    can_upload = bool(collection)
    user_has_upload_perm = request.user.is_uploader or request.user.is_upmaker

    if request.method == 'POST' and can_upload and user_has_upload_perm and request.user.root.client.is_active:
        form_doc = FileDocumentForm(request.POST, request.FILES, request=request, collection=collection)

        if form_doc.is_valid():
            file_doc = form_doc.save()
            UPLOAD_LOGGER.debug(f"""[COLLECTION FILE UPLOAD]
            User: {request.user.username} from IP Address {get_client_ip(request)}
            Uploaded collection file with doc_id: {file_doc.id}""")
            handle_uploaded_file.delay(file_doc.id, language=translation.get_language())
            return HttpResponseRedirect(request.path)               # Redirect to the document list after POST
        else:
            UPLOAD_ERROR_LOGGER.debug(f"""[COLLECTION FILE UPLOAD ERROR]
            Collection upload error: {form_doc.errors['file'][0]}
            By User: {request.user.username} from IP Address {get_client_ip(request)}""")
            return JsonResponse(form_doc.errors, status=400)

    doc_list_collection = Doc.objects.filter(owner__hierarchy=request.user.hierarchy, type_of=Doc.COLLECTION)
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

    def post(self, request, pk=None, *args, **kwargs):
        if not request.is_ajax():
            return JsonResponse(data={}, status=403)

        file_obj = get_object_or_404(Doc, pk=pk, owner__hierarchy=request.user.hierarchy)
        file_obj.delete()
        DELETED_FILES_LOGGER.debug(f"""[FILE DELETED]
        User: {request.user.username} from IP Address {get_client_ip(request)}
        Deleted a file with doc_name: {file_obj.filename()}""")

        return JsonResponse(data={}, status=200)


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
    hide_review_form = True         # True if checker already reviewed this doc or reviews are completed
    can_review = True               # True if checker have the level rights to review the doc
    can_user_disburse = {}
    if doc.owner.hierarchy == request.user.hierarchy:
        # doc already disbursed
        if doc.is_disbursed and (doc.owner == request.user or request.user.is_checker or request.user.is_root):
            return redirect(reverse("disbursement:disbursed_data", args=(doc_id, )))
        if request.user.is_checker:
            # makers must notify checkers and allow the document to be disbursed
            # checker should not have access to doc url or id before that
            if not doc.can_be_disbursed:
                VIEW_DOCUMENT_LOGGER.debug(f"""[DOC CAN NOT BE DISBURSED]
                Document with doc_id {doc_id} can not be disbursed, checker {request.user.username}""")
                raise Http404

            if not doc.is_reviews_completed():
                if doc.is_reviews_rejected():
                    hide_review_form = True
                else:
                    # user_can_review: if can't then can't view the doc
                    # user_review_exist: checks if checker already reviewed this doc
                    user_can_review, user_review_exist = doc.can_user_review(request.user)
                    if not user_can_review and not user_review_exist:
                        can_review = False
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
                    ready_for_disbursement = doc.is_reviews_completed()

                    if ready_for_disbursement:
                        matched_levels_can_disburse = Levels.objects.filter(created=request.user.root).filter(
                                max_amount_can_be_disbursed__gte=doc.total_amount)
                        levels_of_authority = [level.level_of_authority for level in matched_levels_can_disburse]
                        notify_disbursers.delay(doc.id, min(levels_of_authority), language=translation.get_language())

                    # notify checkers of next level if ?
                    # 1 current checker review is ok, and
                    # 2 doc is not ready for disbursement, and
                    # 3 all of the current level of checkers has already reviewed the doc
                    current_level_checkers_can_review = False
                    current_level_checkers = CheckerUser.objects.filter(hierarchy=request.user.hierarchy).filter(
                            level__level_of_authority=request.user.level.level_of_authority)
                    for checker in current_level_checkers:
                        can_user_review, user_already_reviewed = doc.can_user_review(checker)
                        if can_user_review:
                            current_level_checkers_can_review = True

                    if doc_review_obj.is_ok and not ready_for_disbursement and not current_level_checkers_can_review:
                        levels = CheckerUser.objects.filter(hierarchy=request.user.hierarchy).values_list(
                                'level__level_of_authority', flat=True)
                        levels = list(levels)
                        levels = [level for level in levels if level > request.user.level.level_of_authority]
                        if levels:
                            notify_checkers.delay(doc.id, min(levels), language=translation.get_language())
                    # notify the maker either way
                    doc_review_maker_mail.delay(doc.id, doc_review_obj.id, language=translation.get_language())
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
        VIEW_DOCUMENT_LOGGER.debug(f"""[HIERARCHY ERROR]
        User viewing document from other hierarchy, 
        username: {request.user.username}, user hierarchy: {request.user.hierarchy}, 
        doc hierarchy: {doc.owner.hierarchy}, doc id: {doc.id}""")
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
        'doc_data': doc_data,
        'can_review': can_review
    }
    if bool(request.GET.dict()):
        context['redirect'] = 'true'
        context.update(request.GET.dict())
    else:
        context['redirect'] = 'false'

    VIEW_DOCUMENT_LOGGER.debug(f"""[DOC VIEWED]
    User: {request.user.username} from IP Address {get_client_ip(request)}
    Viewed document with doc_id: {doc_id}""")
    return render(request, template_name=template_name, context=context)


@login_required
@setup_required
def protected_serve(request, path, document_root=None, show_indexes=False):
    DOWNLOAD_LOGGER.debug(f"""[DOC DOWNLOADED]
    User: {request.user.username} from IP Address {get_client_ip(request)}
    Downloaded {path}""")
    path = 'documents/' + path

    try:
        doc = get_object_or_404(Doc, file=path)
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
    doc = get_object_or_404(Doc, id=doc_id)

    if doc.owner.hierarchy == request.user.hierarchy:
        try:
            response = HttpResponse(doc.file, content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = 'attachment; filename=%s' % doc.filename()
            response['X-Accel-Redirect'] = '/media/' + doc.file.name
            DOWNLOAD_LOGGER.debug(f"""[DOC DOWNLOADED]
            User: {request.user.username} from IP Address {get_client_ip(request)}
            Downloaded file with doc_id: {doc_id}""")
        except Exception:
            DOWNLOAD_LOGGER.debug(f"""[DOC DOWNLOAD ERROR]
            User: {request.user.username} from IP Address {get_client_ip(request)}
            Tried to download file with doc_id: {doc_id} but 404 was raised""")
            raise Http404
        return response
    else:
        raise Http404


@method_decorator([root_or_maker_or_uploader, setup_required, login_required], name='dispatch')
class FormatListView(TemplateView):
    template_name = "data/formats.html"

    def get_queryset(self):
        if self.request.user.get_status(self.request) == 'collection':
            return Format.objects.filter(hierarchy=self.request.user.hierarchy)
        else:
            return FileCategory.objects.get_by_hierarchy(self.request.user.hierarchy)

    def get_success_url(self):
        return reverse('data:list_format')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        form = kwargs.get('form', None)
        if self.request.user.get_status(self.request) == 'collection':
            context['formatform'] = form or FormatFormSet(
                queryset=self.get_queryset(),
                prefix='format'
            )
            if not self.request.user.is_root:
                context['formatform'].can_delete = False
                context['formatform'].extra = 0
        else:
            context['formatform'] = form or FileCategoryFormSet(
                queryset=self.get_queryset(),
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
            form.save()
            return redirect(self.get_success_url())

        return self.render_to_response(self.get_context_data(form=form))


@method_decorator([collection_users, setup_required, login_required], name='dispatch')
class RetrieveCollectionData(DetailView):
    http_method_names = ['get']
    template_name = "data/document_viewer_collection.html"

    def get_queryset(self, *args, **kwargs):
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
