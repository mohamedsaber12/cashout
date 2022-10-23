from instant_cashin.models import instant_transactions
from rest_framework import serializers

from ..models import DisbursementData


class DisbursementSerializer(serializers.Serializer):
    doc_id = serializers.CharField()
    pin = serializers.CharField()
    user = serializers.CharField()


class DisbursementCallBackSerializer(serializers.ModelSerializer):
    is_disturbed = serializers.BooleanField(source='TXNSTATUS')
    transfer_id = serializers.CharField(source='TRID')
    reason = serializers.CharField(source='MESSAGE')
    doc_id = serializers.PrimaryKeyRelatedField(many=False, read_only=True, source='txnid')

    class Meta:
        model = DisbursementData
        fields = (
            'is_disbursed',
            'transfer_id',
            'msisdn',
            'reason',
            'doc'
        )

    def validate_is_disturbed(self, value):
        if value == 200:
            return True
        else:
            return False

    def update(self, instance, validated_data):
        return super(DisbursementCallBackSerializer, self).update(instance, validated_data)


class DisbursementDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisbursementData
        fields = '__all__'


class InstantTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model =instant_transactions.InstantTransaction
        fields = '__all__'
