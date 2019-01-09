from import_export import resources

from disb.models import DisbursementData


class DisbursementDataResource(resources.ModelResource):
    class Meta:
        model = DisbursementData
        fields = ('amount', 'msisdn')

    def __init__(self, doc, file_category):
        self.file_category = file_category
        self.doc = doc
        self.amount_position = 0
        self.msisdn_position = 0

    def get_export_headers(self):
        headers = self.doc.format.identifiers()
        amount_field = self.file_category.amount_field
        msisdn_field = self.file_category.unique_field
        for pos, header in enumerate(headers):
            if amount_field == header:
                self.amount_position = pos
            elif msisdn_field == header:
                self.msisdn_position = pos
        return headers

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
