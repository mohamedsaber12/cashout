from rest_framework import serializers

from payment.models import Transactions
import re


class TransactionSerializer(serializers.ModelSerializer):
    ref = serializers.IntegerField(source='file_data_id')

    class Meta:
        model = Transactions
        exclude = ('type_of_payment', 'status', 'datetime', 'fine', 'biller')
