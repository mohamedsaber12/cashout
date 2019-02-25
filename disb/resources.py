from import_export import resources

from disb.models import DisbursementData


class DisbursementDataResource(resources.ModelResource):
    class Meta:
        model = DisbursementData
        fields = ('amount', 'msisdn')

    def __init__(self, doc, file_category):
        self.file_category = file_category
        self.doc = doc
        self.amount_position, self.msisdn_position = file_category.fields_cols()

    def get_export_headers(self):
        return ['msisdn','amount']

    def arrange(self, obj_res):
        amount = obj_res[0]
        msisdn = obj_res[1]
        data = ['']*3
        data[self.amount_position] = str(amount)
        data[self.msisdn_position] = msisdn
        return data

    def get_queryset(self):
        qs = super(DisbursementDataResource, self).get_queryset()
        return qs.filter(is_disbursed=0, doc_id=self.doc.id)

    def export_resource(self, obj):
        obj_resources = super(DisbursementDataResource, self).export_resource(obj)
        return self.arrange(obj_resources)
