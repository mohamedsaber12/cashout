# Create your views here.
from __future__ import print_function, unicode_literals

import logging

import xlrd
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import (Http404, HttpResponse, HttpResponseRedirect,
                         JsonResponse)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import translation
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_safe
from django.views.generic import DetailView, TemplateView, View
from django.views.static import serve
from instant_cashin.utils import get_from_env

from disbursement.utils import (BANK_CODES,
                                BANK_TRANSACTION_TYPES_DESCRIPTION_LIST)
from users.decorators import (collection_users, disbursement_users, root_only,
                              setup_required)
from users.mixins import (SupportOrRootOrMakerUserPassesTestMixin,
                          UserWithAcceptVFOnboardingPermissionRequired,
                          UserWithDisbursementPermissionRequired)
from users.models import CheckerUser, Levels
from utilities.models import AbstractBaseDocType

from .forms import (DocReviewForm, FileCategoryFormSet, FileDocumentForm,
                    FormatFormSet, RecuringForm,
                    ReportProblemOnTransactionForm)
from .models import CollectionData, Doc, DocReview, FileCategory, Format
from .tasks import (BankWalletsAndCardsSheetProcessor, EWalletsSheetProcessor,
                    doc_review_maker_mail, handle_uploaded_file,
                    notify_checkers, notify_disbursers)
import requests
import json
UPLOAD_LOGGER = logging.getLogger("upload")
DELETED_FILES_LOGGER = logging.getLogger("deleted_files")
UNAUTHORIZED_FILE_DELETE_LOGGER = logging.getLogger("unauthorized_file_delete")
DOWNLOAD_LOGGER = logging.getLogger("download_serve")
VIEW_DOCUMENT_LOGGER = logging.getLogger("view_document")


@require_safe
@login_required
@setup_required
def redirect_home(request):
    if request.user.is_accept_vodafone_onboarding and (
        request.user.is_checker or request.user.is_maker
    ):
        return redirect(reverse("disbursement:home_root"))
    if (
        request.user.is_root
        and request.user.from_accept
        and not request.user.allowed_to_be_bulk
    ):
        return redirect(reverse(f"disbursement:single_step_list_create"))
    if request.user.is_root and (
        request.user.is_accept_vodafone_onboarding
        or request.user.is_instant_model_onboarding
    ):
        return redirect(reverse("disbursement:home_root"))
    if request.user.is_instantapiviewer:
        return redirect(reverse("disbursement:home_root"))
    if request.user.is_superuser:
        return redirect(reverse("admin:index"))
    if request.user.is_finance:
        return redirect(reverse("admin:index"))
    if request.user.is_vodafone_monthly_report:
        return redirect(reverse("admin:index"))
    if request.user.is_finance_with_instant_transaction_view:
        return redirect(reverse("admin:index"))
    if request.user.is_single_step_support:
        return redirect(reverse("admin:index"))
    elif request.user.is_support:
        return redirect(reverse("users:support_home"))
    elif request.user.is_onboard_user:
        return redirect(reverse("users:onboard_user_home"))
    elif request.user.is_supervisor:
        return redirect(reverse("users:supervisor_home"))
    elif request.user.is_instant_model_onboarding:
        return redirect(reverse("instant_cashin:wallets_trx_list"))

    else:
        return redirect(f"data:e_wallets_home")


@method_decorator([setup_required], name="dispatch")
class DisbursementHomeView(UserWithDisbursementPermissionRequired, View):
    """
    Home view for disbursement related users ex. Admin/Maker/Checker
    """

    def dispatch(self, request, *args, **kwargs):
        """
        Common attributes between GET and POST methods
        """
        self.doc_type = AbstractBaseDocType.E_WALLETS
        self.user_has_upload_perm = request.user.is_maker or request.user.is_upmaker
        self.admin_is_active = request.user.root.client.is_active
        self.family_file_categories = FileCategory.objects.get_by_hierarchy(
            request.user.hierarchy
        )
        self.has_any_file_category = bool(self.family_file_categories)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        Lists all documents related to the currently logged in user hierarchy.
        Users: Any Admin/Maker/Checker user can view his family list of disbursement documents.
        Notes:
            1. Documents can be filtered by date.
            2. Documents are paginated but not used in template.
        """
        has_vmt_setup = request.user.root.has_vmt_setup
        doc_list_disbursement = Doc.objects.filter(
            owner__hierarchy=request.user.hierarchy, type_of=self.doc_type
        )
        paginator = Paginator(doc_list_disbursement, 7)
        page = request.GET.get("page")
        docs = paginator.get_page(page)

        context = {
            "has_vmt_setup": has_vmt_setup,
            "admin_is_active": self.admin_is_active,
            "family_file_categories": self.family_file_categories,
            "has_any_file_category": self.has_any_file_category,
            "user_has_upload_perm": self.user_has_upload_perm,
            "doc_list_disbursement": docs,
        }

        return render(request, "data/e_wallets_home.html", context=context)

    def post(self, request, *args, **kwargs):
        """
        Allows maker users to upload a disbursement file which complies with certain file category.
        The file is later processed by the task 'handle_disbursement_file'.
        """
        if (
            self.has_any_file_category
            and self.user_has_upload_perm
            and self.admin_is_active
        ):
            form_doc = FileDocumentForm(
                request.POST, request.FILES, request=request, doc_type=self.doc_type
            )

            if form_doc.is_valid():
                file_doc = form_doc.save()
                file_doc.mark_uploaded_successfully()
                msg = f"uploaded e-wallets file with doc id: {file_doc.id}"
                UPLOAD_LOGGER.debug(
                    f"[message] [e-wallets file upload] [{request.user}] -- {msg}"
                )
                EWalletsSheetProcessor.delay(file_doc.id)
                return HttpResponseRedirect(
                    request.path
                )  # Redirect to the document list after successful POST
            else:
                UPLOAD_LOGGER.debug(
                    f"[message] [e-wallets file upload error] [{request.user}] -- {form_doc.errors['file'][0]}"
                )
                return JsonResponse(form_doc.errors, status=400)
        else:
            UPLOAD_LOGGER.debug(
                f"[message] [e-wallets file upload error] [{request.user}] -- Upload permissions not fulfilled"
            )
            return HttpResponseRedirect(request.path)


@method_decorator([setup_required], name="dispatch")
class BanksHomeView(
    UserWithAcceptVFOnboardingPermissionRequired,
    UserWithDisbursementPermissionRequired,
    View,
):
    """
    Home view for bank wallets/cards disbursements, users ex. Admin/Maker/Checker with accept-vf onboarding permissions
    """

    def dispatch(self, request, *args, **kwargs):
        """
        Common attributes between GET and POST methods
        """
        if "bank-wallets" in request.path:
            self.doc_type = AbstractBaseDocType.BANK_WALLETS
            self.doc_list_header = "Bank wallets/Orange cash"
        elif "bank-cards" in request.path:
            self.doc_type = AbstractBaseDocType.BANK_CARDS
            self.doc_list_header = "Bank Accounts/Cards"
        else:
            return HttpResponseRedirect(request.path)
        self.admin_is_active = request.user.root.client.is_active
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        Lists all documents related to the currently logged in user hierarchy.
        Users: Any Admin/Maker/Checker user can view his family list of disbursement documents.
        Notes:
            1. Documents can be filtered by date.
            2. Documents are paginated but not used in template.
        """
        has_vmt_setup = request.user.root.has_vmt_setup
        banks_doc_list = Doc.objects.filter(
            owner__hierarchy=request.user.hierarchy, type_of=self.doc_type
        )
        paginator = Paginator(banks_doc_list, 7)
        page = request.GET.get("page")
        docs = paginator.get_page(page)

        context = {
            "has_vmt_setup": has_vmt_setup,
            "admin_is_active": self.admin_is_active,
            "banks_doc_list": docs,
            "bank_codes": BANK_CODES,
            "transaction_type_desc_list": BANK_TRANSACTION_TYPES_DESCRIPTION_LIST,
            "doc_list_header": self.doc_list_header,
        }

        return render(request, "data/bank_sheets_home.html", context=context)

    def post(self, request, *args, **kwargs):
        """
        Allows maker users to upload bank wallets/cards disbursement files which complies with certain predefined format
        The file is later processed by the task 'process_bank_wallets_sheet' or 'process_bank_cards_sheet'.
        """
        if self.admin_is_active:
            form_doc = FileDocumentForm(
                request.POST, request.FILES, request=request, doc_type=self.doc_type
            )

            if form_doc.is_valid():
                file_doc = form_doc.save()
                file_doc.mark_uploaded_successfully()
                msg = f"uploaded {self.doc_list_header.lower()} file with doc id: {file_doc.id}"
                UPLOAD_LOGGER.debug(
                    f"[message] [{self.doc_list_header.lower()} file upload] [{request.user}] -- {msg}"
                )
                BankWalletsAndCardsSheetProcessor.delay(file_doc.id)
                return HttpResponseRedirect(request.path)
            else:
                UPLOAD_LOGGER.debug(
                    f"[message] [{self.doc_list_header.lower()} file upload error] [{request.user}] -- "
                    f"{form_doc.errors['file'][0]}"
                )
                return JsonResponse(form_doc.errors, status=400)
        else:
            return HttpResponseRedirect(request.path)


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
        user__hierarchy=request.user.hierarchy
    ).first()
    can_upload = bool(collection)
    user_has_upload_perm = request.user.is_uploader or request.user.is_upmaker

    if (
        request.method == "POST"
        and can_upload
        and user_has_upload_perm
        and request.user.root.client.is_active
    ):
        form_doc = FileDocumentForm(
            request.POST, request.FILES, request=request, collection=collection
        )

        if form_doc.is_valid():
            file_doc = form_doc.save()
            msg = f"uploaded collection file with doc_id: {file_doc.id}"
            UPLOAD_LOGGER.debug(
                f"[message] [COLLECTION FILE UPLOAD] [{request.user}] -- {msg}"
            )
            handle_uploaded_file.delay(
                file_doc.id, language=translation.get_language())
            return HttpResponseRedirect(
                request.path
            )  # Redirect to the document list after POST
        else:
            msg = f"collection upload error: {form_doc.errors['file'][0]}"
            UPLOAD_LOGGER.debug(
                f"[message] [COLLECTION FILE UPLOAD ERROR] [{request.user}] -- {msg}"
            )
            return JsonResponse(form_doc.errors, status=400)

    doc_list_collection = Doc.objects.filter(
        owner__hierarchy=request.user.hierarchy, type_of=Doc.COLLECTION
    )
    context = {
        "doc_list_collection": doc_list_collection,
        "format_qs": format_qs,
        "can_upload": can_upload,
        "user_has_upload_perm": user_has_upload_perm,
    }

    return render(request, "data/collection_home.html", context=context)


@method_decorator([root_only, setup_required, login_required], name="dispatch")
class FileDeleteView(View):
    """
    Function that deletes a file
    """

    def post(self, request, pk=None, *args, **kwargs):
        if not request.is_ajax():
            return JsonResponse(data={}, status=403)

        file_obj = get_object_or_404(
            Doc, pk=pk, owner__hierarchy=request.user.hierarchy
        )
        if file_obj.is_disbursed:
            return JsonResponse(data={}, status=403)
        file_obj.delete()
        msg = f"deleted a file with doc_name: {file_obj.filename()}"
        DELETED_FILES_LOGGER.debug(
            f"[message] [FILE DELETED] [{request.user}] -- {msg}"
        )

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
    doc = get_object_or_404(Doc, id=doc_id)
    doc_transactions = None
    review_form_errors = None
    recuring_form_errors = None
    reviews = None
    hide_review_form = (
        True  # True if checker already reviewed this doc or reviews are completed
    )
    can_review = True  # True if checker have the level rights to review the doc
    can_user_disburse = {}

    # 1. Check if the user who make the request is from the same hierarchy
    if doc.owner.hierarchy == request.user.hierarchy:
        # doc already disbursed
        if doc.is_disbursed and (
            doc.owner == request.user or request.user.is_checker or request.user.is_root
        ):
            VIEW_DOCUMENT_LOGGER.debug(
                f"[message] [DOC VIEWED] [{request.user}] -- viewed doc with ID: {doc_id}"
            )
            return redirect(reverse("disbursement:disbursed_data", args=(doc_id,)))
        if request.user.is_checker:
            # makers must notify checkers and allow the document to be disbursed
            # checker should not have access to doc url or id before that
            if not doc.can_be_disbursed:
                msg = f"current checker can't disburse doc with ID: {doc_id}"
                VIEW_DOCUMENT_LOGGER.debug(
                    f"[message] [DOC CAN NOT BE DISBURSED] [{request.user}] -- {msg}"
                )
                raise Http404

            if not doc.is_reviews_completed():
                if doc.is_reviews_rejected():
                    hide_review_form = True
                else:
                    # user_can_review: if can't then can't view the doc
                    # user_review_exist: checks if checker already reviewed this doc
                    user_can_review, user_review_exist = doc.can_user_review(
                        request.user
                    )
                    if not user_can_review and not user_review_exist:
                        can_review = False
                    # user can review then user review doesn't exist then show review form
                    hide_review_form = user_review_exist
            reviews = DocReview.objects.filter(doc=doc)

            if request.method == "POST" and not hide_review_form:
                if not can_review:
                    err_msg = f"current checker is still unprivileged to review doc with ID: {doc.id}"
                    VIEW_DOCUMENT_LOGGER.debug(
                        f"[message] [PRIVILEGES ERROR] [{request.user}] -- {err_msg}"
                    )
                    raise PermissionDenied(
                        _("You still do not have the right to review this document.")
                    )

                doc_review_form = DocReviewForm(request.POST)
                if doc_review_form.is_valid():
                    doc_review_obj = doc_review_form.save(commit=False)
                    doc_review_obj.user_created = request.user
                    doc_review_obj.doc = doc
                    doc_review_obj.save()
                    ready_for_disbursement = doc.is_reviews_completed()

                    if ready_for_disbursement:
                        matched_levels_can_disburse = Levels.objects.filter(
                            created=request.user.root
                        ).filter(max_amount_can_be_disbursed__gte=doc.total_amount)
                        levels_of_authority = [
                            level.level_of_authority
                            for level in matched_levels_can_disburse
                        ]
                        notify_disbursers.delay(
                            doc.id,
                            min(levels_of_authority),
                            language=translation.get_language(),
                        )

                    # notify checkers of next level if ?
                    # 1 current checker review is ok, and
                    # 2 doc is not ready for disbursement, and
                    # 3 all of the current level of checkers has already reviewed the doc
                    current_level_checkers_can_review = False
                    current_level_checkers = CheckerUser.objects.filter(
                        hierarchy=request.user.hierarchy
                    ).filter(
                        level__level_of_authority=request.user.level.level_of_authority
                    )
                    for checker in current_level_checkers:
                        can_user_review, user_already_reviewed = doc.can_user_review(
                            checker
                        )
                        if can_user_review:
                            current_level_checkers_can_review = True

                    if (
                        doc_review_obj.is_ok
                        and not ready_for_disbursement
                        and not current_level_checkers_can_review
                    ):
                        levels = CheckerUser.objects.filter(
                            hierarchy=request.user.hierarchy
                        ).values_list("level__level_of_authority", flat=True)
                        levels = list(levels)
                        levels = [
                            level
                            for level in levels
                            if level > request.user.level.level_of_authority
                        ]
                        if levels:
                            notify_checkers.delay(
                                doc.id, min(levels), language=translation.get_language()
                            )
                    # notify the maker either way
                    doc_review_maker_mail.delay(
                        doc.id, doc_review_obj.id, language=translation.get_language()
                    )
                    hide_review_form = True
                else:
                    review_form_errors = doc_review_form.errors["comment"][0]
            can_user_disburse = doc.can_user_disburse(request.user)
            can_user_disburse = {
                "can_disburse": can_user_disburse[0],
                "reason": can_user_disburse[1],
                "code": can_user_disburse[2],
            }

    # 2. The user who is trying to access the doc is NOT from the same hierarchy (NOT privileged)
    else:
        err_msg = f"doc id: {doc.id} with hierarchy: {doc.owner.hierarchy}, user hierarchy: {request.user.hierarchy}"
        VIEW_DOCUMENT_LOGGER.debug(
            f"[message] [HIERARCHY ERROR] [{request.user}] -- {err_msg}"
        )
        return redirect(reverse("data:e_wallets_home"))

    if request.method == "POST" and request.user.is_maker:
        recuring_form = RecuringForm(request.POST)
        recuring_form_errors = recuring_form.errors
        if recuring_form.is_valid():
            cleaned_data = recuring_form.cleaned_data
            doc.recuring_period = cleaned_data.get("recuring_period")
            doc.is_recuring = cleaned_data.get("is_recuring")
            if doc.recuring_starting_date != cleaned_data.get("recuring_starting_date"):
                doc.recuring_latest_date = cleaned_data.get(
                    "recuring_starting_date")
            doc.recuring_starting_date = cleaned_data.get(
                "recuring_starting_date")
            doc.save()

    # 3. Retrieve the document related transactions to be viewed
    if doc.is_processed and doc.is_e_wallet:
        doc_transactions = doc.disbursement_data.all()
    elif doc.is_processed and doc.is_bank_wallet:
        doc_transactions = doc.bank_wallets_transactions.all()
    elif doc.is_processed and doc.is_bank_card:
        doc_transactions = doc.bank_cards_transactions.all()

    template_name = (
        "data/e_wallets_document_viewer.html"
        if doc.is_e_wallet
        else "data/banks_document_viewer.html"
    )

    # 4. Prepare the context dict to be passed to the template
    context = {
        "doc": doc,
        "review_form_errors": review_form_errors,
        "reviews": reviews,
        "hide_review_form": hide_review_form,
        "can_user_disburse": can_user_disburse,
        "doc_transactions": doc_transactions,
        "can_review": can_review,
        "is_normal_flow": request.user.root.root_entity_setups.is_normal_flow,
        "recuring_form_errors": recuring_form_errors,
    }

    # 5. Handle document auto-redirects after disbursement action related to different responses
    if bool(request.GET.dict()):
        context["redirect"] = "true"
        context.update(request.GET.dict())
    else:
        context["redirect"] = "false"

    VIEW_DOCUMENT_LOGGER.debug(
        f"[message] [DOC VIEWED] [{request.user}] -- viewed doc with ID: {doc_id}"
    )
    return render(request, template_name=template_name, context=context)


@login_required
@setup_required
def protected_serve(request, path, document_root=None, show_indexes=False):
    """ """

    path = "documents/" + path

    try:
        doc = get_object_or_404(Doc, file=path)
        if doc.owner.hierarchy == request.user.hierarchy:
            DOWNLOAD_LOGGER.debug(
                f"[message] [DOC DOWNLOADED] [{request.user}] -- downloaded doc: {doc}"
            )
            return serve(request, path, document_root, show_indexes)
        else:
            return redirect("data:main_view")
    except Doc.DoesNotExist:
        return serve(request, path, document_root, show_indexes)
    except Doc.MultipleObjectsReturned:
        return redirect("data:main_view")


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
            response = HttpResponse(
                doc.file, content_type="application/vnd.ms-excel")
            response["Content-Disposition"] = "attachment; filename=%s" % doc.filename()
            response["X-Accel-Redirect"] = "/media/" + doc.file.name
            DOWNLOAD_LOGGER.debug(
                f"[message] [DOC DOWNLOADED] [{request.user}] -- downloaded doc ID: {doc_id}"
            )
        except Exception:
            msg = f"tried to download doc with ID: {doc_id} but 404 was raised"
            DOWNLOAD_LOGGER.debug(
                f"[message] [DOC DOWNLOAD ERROR] [{request.user}] -- {msg}"
            )
            raise Http404
        return response
    else:
        raise Http404


@method_decorator([setup_required], name="dispatch")
class FormatListView(SupportOrRootOrMakerUserPassesTestMixin, TemplateView):
    """
    List and update existing file formats of Admin users disbursement/collection
    """

    template_name = "data/formats.html"

    def dispatch(self, request, *args, **kwargs):
        """Common attributes between GET and POST methods"""
        self.is_disbursement_model = (
            True if request.user.get_status(
                self.request) == "disbursement" else False
        )
        self.is_support_model = True if self.request.user.is_support else False
        self.flow_type = (
            self.request.user.root_entity_setups.is_normal_flow
            if self.request.user.is_root
            else False
        )
        self.admin_username = self.request.GET.get("admin", None)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Based on the Admin status decide which type of file format will be used"""
        if self.is_disbursement_model:
            return FileCategory.objects.get_by_hierarchy(self.request.user.hierarchy)
        elif self.is_support_model:
            return FileCategory.objects.filter(
                user_created__username=self.admin_username
            )
        return Format.objects.filter(hierarchy=self.request.user.hierarchy)

    def get_success_url(self):
        """Redirect URL after saving edits successfully"""
        return reverse("data:list_format")

    def get_context_data(self, *args, **kwargs):
        """Inject Variables to the view based on the Admin user type"""
        context = super().get_context_data(*args, **kwargs)
        form = kwargs.get("form", None)

        if self.is_disbursement_model or self.is_support_model:
            context["is_normal_flow"] = self.flow_type
            context["formatform"] = form or FileCategoryFormSet(
                queryset=self.get_queryset(), prefix="category"
            )
        else:
            context["formatform"] = form or FormatFormSet(
                queryset=self.get_queryset(), prefix="format"
            )

        if not self.request.user.is_root:
            context["formatform"].can_delete = False
            context["formatform"].extra = 0
            context["empty_formatform"] = (
                True if context["formatform"].queryset.count() == 0 else False
            )

        return context

    def post(self, request, *args, **kwargs):
        """Handles POST requests to update file formats"""
        if self.is_disbursement_model:
            form = FileCategoryFormSet(
                request.POST, prefix="category", form_kwargs={"request": request}
            )
        else:
            form = FormatFormSet(
                request.POST, prefix="format", form_kwargs={"request": request}
            )

        if form and form.is_valid():
            form.save()
            return redirect(self.get_success_url())

        return self.render_to_response(self.get_context_data(form=form))


@method_decorator([collection_users, setup_required, login_required], name="dispatch")
class RetrieveCollectionData(DetailView):
    http_method_names = ["get"]
    template_name = "data/document_viewer_collection.html"

    def get_queryset(self, *args, **kwargs):
        return Doc.objects.filter(id=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doc_obj = context["object"]
        xl_workbook = xlrd.open_workbook(doc_obj.file.path)
        xl_sheet = xl_workbook.sheet_by_index(0)

        excl_data = []
        for row in xl_sheet.get_rows():
            row_data = []
            for x, data in enumerate(row):
                row_data.append(data.value)
            excl_data.append(row_data)

        context["excel_data"] = excl_data
        return context


class ReportProblemView(LoginRequiredMixin, View):
    """
    view for report a problem on specific transaction
    """

    template_name = 'data/report_problem.html'

    def get(self, request, *args, **kwargs):
        """Handles GET requests for report a problem on transaction Request"""
        context = {
            'form': ReportProblemOnTransactionForm(),
        }
        return render(request, template_name=self.template_name, context=context)

    def post(self, request, *args, **kwargs):
        """Handles POST requests increase balance request"""
        context = {
            'form': ReportProblemOnTransactionForm(request.POST),
        }

        if context['form'].is_valid():
            # integrate with fresh Desk
            cleaned_data = context['form'].cleaned_data
            problem_severity = cleaned_data.get('problem_severity')
            contact_number = cleaned_data.get('contact_number')
            contact_email = cleaned_data.get('contact_email')
            comment = cleaned_data.get('comment')
            if problem_severity == 'low':
                priority = 1
            elif problem_severity == 'med':
                priority = 2
            else:
                priority = 3
            api_key = get_from_env("API_KEY")
            domain = get_from_env("DOMAIN")
            password = get_from_env("FRESHDESK_PASSWORD")
            group_id = get_from_env("GROUP_ID")
            business_team = [
                email
                for email in get_from_env('BUSINESS_TEAM_EMAILS_LIST').split(',')
            ]
            headers = {'Content-Type': 'application/json'}
            ticket = {
                'subject': ' Report A Problem ',
                'description': comment,
                'email': contact_email,
                'phone': contact_number,
                'priority': priority,
                'status': 2,
                'group_id': int(group_id),
                'cc_emails': business_team
            }
            print(group_id)
            r = requests.post("https://" + domain + ".freshdesk.com/api/v2/tickets",
                              auth=(api_key, password), headers=headers, data=json.dumps(ticket))
            if r.status_code == 201:
                context = {
                    'request_received': True,
                    'form': ReportProblemOnTransactionForm(),
                }
            else:
                context = {
                    'request_received': False,
                    'form': ReportProblemOnTransactionForm(),
                }
        return render(request, template_name=self.template_name, context=context)
