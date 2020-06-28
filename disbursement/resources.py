from import_export import resources
from import_export.fields import Field

from .models import DisbursementData


class DisbursementDataResource(resources.ModelResource):
    disbursed = Field(attribute='get_is_disbursed')

    class Meta:
        model = DisbursementData
        fields = ['amount', 'msisdn', 'disbursed', 'reason']
        export_order = ['msisdn', 'amount', 'disbursed', 'reason']

    def __init__(self, doc, file_category, is_disbursed):
        self.doc = doc
        self.is_disbursed = is_disbursed

    def get_export_headers(self):
        return ['Mobile Number', 'Amount', 'Disbursement Status', 'Failure Reason']

    def get_queryset(self):
        qs = super(DisbursementDataResource, self).get_queryset()
        if self.is_disbursed is None:
            return qs.filter(doc_id=self.doc.id)
        else:    
            return qs.filter(is_disbursed=self.is_disbursed, doc_id=self.doc.id)

    def export_resource(self, obj):
        obj_resources = super(DisbursementDataResource, self).export_resource(obj)
        return obj_resources
