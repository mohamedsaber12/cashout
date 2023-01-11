from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from users.models import User

from ..models import DisbursementData


class DisbursementSerializer(serializers.Serializer):
    doc_id = serializers.CharField()
    pin = serializers.CharField()
    user = serializers.CharField()


class DisbursementCallBackSerializer(serializers.ModelSerializer):
    is_disturbed = serializers.BooleanField(source='TXNSTATUS')
    transfer_id = serializers.CharField(source='TRID')
    reason = serializers.CharField(source='MESSAGE')
    doc_id = serializers.PrimaryKeyRelatedField(
        many=False, read_only=True, source='txnid'
    )

    class Meta:
        model = DisbursementData
        fields = ('is_disbursed', 'transfer_id', 'msisdn', 'reason', 'doc')

    def validate_is_disturbed(self, value):
        if value == 200:
            return True
        else:
            return False

    def update(self, instance, validated_data):
        return super(DisbursementCallBackSerializer, self).update(
            instance, validated_data
        )


class Merchantserializer(serializers.Serializer):

    username = serializers.CharField(max_length=100, required=True)

    mobile_number = serializers.CharField(max_length=100, required=True)

    email = serializers.EmailField(max_length=100, required=False)

    idms_user_id = serializers.CharField(max_length=100, required=True)

    mid = serializers.IntegerField(required=True)

    def validate(self, attr):

        is_required_msg = 'This field is required'

        if not attr.get('username'):
            raise serializers.ValidationError(_(f"username {is_required_msg}"))
        if not attr.get('mobile_number'):
            raise serializers.ValidationError(_(f"mobile_number {is_required_msg}"))
        if not attr.get('idms_user_id'):
            raise serializers.ValidationError(_(f"idms_user_id {is_required_msg}"))
        if not attr.get('mid'):
            raise serializers.ValidationError(_(f"mid {is_required_msg}"))
        user_name = attr.get("username")
        idms_user_id = attr.get("idms_user_id")
        email = attr.get("email")
        root = User.objects.filter(idms_user_id=idms_user_id).exclude(
            username=user_name
        )
        if root.exists():
            raise serializers.ValidationError(
                _(f"idms is already taken by another admin.")
            )

        _root = User.objects.filter(email=email).exclude(username=user_name)
        if _root.exists():
            raise serializers.ValidationError(
                _(f"email is already taken by another admin.")
            )

        return attr
