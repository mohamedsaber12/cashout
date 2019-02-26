from import_export import resources

from disb.models import DisbursementData


class DisbursementDataResource(resources.ModelResource):
    class Meta:
        model = DisbursementData
        fields = ('amount', 'msisdn')

    def __init__(self, doc, file_category):
        self.doc = doc

    def get_export_headers(self):
        return ['amount', 'msisdn']

    def get_queryset(self):
        qs = super(DisbursementDataResource, self).get_queryset()
        return qs.filter(is_disbursed=0, doc_id=self.doc.id)

    def export_resource(self, obj):
        obj_resources = super(DisbursementDataResource, self).export_resource(obj)
        return obj_resources
