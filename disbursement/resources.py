from import_export import resources
from import_export.fields import Field

from core.models import AbstractBaseStatus
from instant_cashin.models.instant_transactions import InstantTransaction

from .models import BankTransaction, DisbursementData
from .utils import get_error_description_from_error_code


class DisbursementDataResourceForEWallets(resources.ModelResource):
    """
    Resource for exporting e-wallets transactions reports
    """

    disbursed = Field(attribute='get_is_disbursed')

    class Meta:
        model = DisbursementData
        fields = ['amount', 'msisdn', 'disbursed', 'reason']
        export_order = ['msisdn', 'amount', 'disbursed', 'reason']

    def __init__(self, doc, is_disbursed):
        self.doc = doc
        self.is_disbursed = is_disbursed

    def get_export_headers(self):
        return ['Mobile Number', 'Amount', 'Disbursement Status', 'Failure Reason']

    def get_queryset(self):
        qs = super().get_queryset()

        if self.is_disbursed is None:
            return qs.filter(doc_id=self.doc.id)
        else:    
            return qs.filter(is_disbursed=self.is_disbursed, doc_id=self.doc.id)

    def export_resource(self, obj):
        obj_resources = super().export_resource(obj)

        if obj_resources[2] == 'Failed':
            obj_resources[3] = get_error_description_from_error_code(obj_resources[3])
        return obj_resources


class DisbursementDataResourceForBankWallet(resources.ModelResource):
    """
    Resource for exporting bank wallets/orange transactions reports
    """

    transaction_status = Field(attribute='status_choice_verbose')

    class Meta:
        model = InstantTransaction
        fields = [
            'anon_recipient', 'amount', 'recipient_name', 'transaction_status', 'transaction_status_code',
            'transaction_status_description'
        ]
        export_order = [
            'anon_recipient', 'amount', 'recipient_name', 'transaction_status', 'transaction_status_code',
            'transaction_status_description'
        ]

    def __init__(self, doc, is_disbursed):
        self.doc = doc
        self.is_disbursed = is_disbursed

    def get_export_headers(self):
        return [
            'Mobile Number', 'Amount', 'Full Name', 'Disbursement Status', 'Disbursement Status Code',
            'Disbursement Status Description'
        ]

    def get_queryset(self):
        qs = super().get_queryset()

        if self.is_disbursed is None:
            return qs.filter(document_id=self.doc.id)
        elif self.is_disbursed == False:
            return qs.filter(status=AbstractBaseStatus.FAILED, document_id=self.doc.id)
        else:
            return qs.filter(status=AbstractBaseStatus.SUCCESSFUL, document_id=self.doc.id)


class DisbursementDataResourceForBankCards(resources.ModelResource):
    """
    Resource for exporting bank accounts/cards transactions reports
    """

    transaction_type = Field(attribute='get_transaction_type')
    transaction_status = Field(attribute='status_choice_verbose')

    class Meta:
        model = BankTransaction
        fields = [
            'creditor_account_number', 'amount', 'creditor_name', 'creditor_bank', 'transaction_type',
            'transaction_status', 'transaction_status_code', 'transaction_status_description'
        ]
        export_order = [
            'creditor_account_number', 'amount', 'creditor_name', 'creditor_bank', 'transaction_type',
            'transaction_status', 'transaction_status_code', 'transaction_status_description'
        ]

    def __init__(self, doc, is_disbursed):
        self.doc = doc
        self.is_disbursed = is_disbursed

    def get_export_headers(self):
        return [
            'Account Number', 'Amount', 'Full Name', 'Bank Code', 'Transaction Type',
            'Disbursement Status', 'Disbursement Status Code', 'Disbursement Status Description'
        ]

    def get_queryset(self):
        qs = super().get_queryset()

        if self.is_disbursed is None:
            return qs.filter(document_id=self.doc.id)
        elif self.is_disbursed == False:
            return qs.filter(status=AbstractBaseStatus.FAILED, document_id=self.doc.id)
        else:
            return qs.filter(status=AbstractBaseStatus.SUCCESSFUL, document_id=self.doc.id)
