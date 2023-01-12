from django.utils.translation import gettext as _

from instant_cashin.models import instant_transactions
from rest_framework import serializers
from users.models.base_user import User
from users.models.root import RootUser
from disbursement.utils import VALID_BANK_CODES_LIST

from users.models import User

from ..models import DisbursementData


class DisbursementSerializer(serializers.Serializer):
    doc_id = serializers.CharField()
    pin = serializers.CharField()
    user = serializers.CharField()


class DisbursementCallBackSerializer(serializers.ModelSerializer):
    is_disturbed = serializers.BooleanField(source="TXNSTATUS")
    transfer_id = serializers.CharField(source="TRID")
    reason = serializers.CharField(source="MESSAGE")
    doc_id = serializers.PrimaryKeyRelatedField(
        many=False, read_only=True, source="txnid"
    )

    class Meta:
        model = DisbursementData
        fields = ("is_disbursed", "transfer_id", "msisdn", "reason", "doc")

    def validate_is_disturbed(self, value):
        if value == 200:
            return True
        else:
            return False

    def update(self, instance, validated_data):
        return super(DisbursementCallBackSerializer, self).update(
            instance, validated_data
        )


class CreateMerchantserializer(serializers.Serializer):

    username = serializers.CharField(max_length=100, required=True)

    mobile_number = serializers.CharField(max_length=100, required=False)

    email = serializers.EmailField(max_length=100, required=True)

    idms_user_id = serializers.CharField(max_length=100, required=True)

    mid = serializers.IntegerField(required=True)

    def validate(self, attr):

        is_required_msg = "This field is required"

        if not attr.get("username"):
            raise serializers.ValidationError(_(f"username {is_required_msg}"))
        if not attr.get("idms_user_id"):
            raise serializers.ValidationError(_(f"idms_user_id {is_required_msg}"))
        if not attr.get("mid"):
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


class DisbursementDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisbursementData
        fields = "__all__"


class InstantTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = instant_transactions.InstantTransaction
        fields = "__all__"


class SingleStepserializer(serializers.Serializer):

    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    issuer = serializers.CharField(max_length=100, required=True)
    username = serializers.CharField(max_length=100, required=True)

    transaction_type = serializers.CharField(max_length=100, required=False)
    creditor_account_number = serializers.CharField(max_length=100, required=False)
    creditor_name = serializers.CharField(max_length=100, required=False)
    creditor_bank = serializers.CharField(max_length=100, required=False)
    # 3. shared filed between vodafone, etisalat, aman, orange, bank wallet

    msisdn = serializers.CharField(required=False)
    # 4. shared fields between orange, bank wallet
    full_name = serializers.CharField(max_length=100, required=False)
    # aman fields
    full_name = serializers.CharField(max_length=100, required=False)
    first_name = serializers.CharField(max_length=100, required=False)
    last_name = serializers.CharField(max_length=100, required=False)
    admin_email = serializers.EmailField(max_length=100, required=True)
    email = serializers.EmailField(max_length=100, required=False)
    idms_user_id = serializers.CharField(max_length=100, required=True)

    def validate(self, attr):
        is_required_msg = "This field is required"
        issuer = attr.get("issuer", "")
        if not issuer in [
            "bank_card",
            "vodafone",
            "etisalat",
            "orange",
            "bank_wallet",
            "aman",
        ]:
            raise serializers.ValidationError(
                _(
                    "issuer type must be (bank_card or vodafone or etisalat or orange or bank_wallet or aman )."
                )
            )
        if issuer == "bank_card":
            if not attr.get("full_name"):
                raise serializers.ValidationError(_(f"fullname {is_required_msg}"))
            elif not attr.get("creditor_account_number"):
                raise serializers.ValidationError(
                    _(f"creditor_account_number {is_required_msg}")
                )

            if not attr.get("transaction_type"):
                raise serializers.ValidationError(
                    _(f"transaction_type {is_required_msg}")
                )
            if not attr.get("transaction_type") in [
                "CASH_TRANSFER",
                "SALARY",
                "PREPAID_CARD",
                "CREDIT_CARD",
            ]:
                raise serializers.ValidationError(
                    _(
                        f"transaction_type must be one of this ( CASH_TRANSFER, SALARY, PREPAID_CARD, CREDIT_CARD ) "
                    )
                )

            if not attr.get("creditor_bank"):
                raise serializers.ValidationError(_(f"creditor_bank {is_required_msg}"))
            if not attr.get("creditor_bank") in VALID_BANK_CODES_LIST:
                raise serializers.ValidationError(
                    _(f"transaction_type must be one of VALID_BANK_CODES_LIST ")
                )
        elif issuer == "aman":
            if not attr.get("first_name"):
                raise serializers.ValidationError(_(f"first_name {is_required_msg}"))
            if not attr.get("last_name"):
                raise serializers.ValidationError(_(f"last_name {is_required_msg}"))
            if not attr.get("email"):
                raise serializers.ValidationError(_(f"email {is_required_msg}"))
            if not attr.get("msisdn"):
                raise serializers.ValidationError(_(f"msisdn {is_required_msg}"))
        if issuer == "vodafone" or issuer == "etisalat":
            if not attr.get("msisdn"):
                raise serializers.ValidationError(_(f"msisdn {is_required_msg}"))
        if issuer == "orange" or issuer == "bank_wallet":
            if not attr.get("msisdn"):
                raise serializers.ValidationError(_(f"msisdn {is_required_msg}"))
            if not attr.get("full_name"):
                raise serializers.ValidationError(_(f"full_name {is_required_msg}"))

        user_name = attr.get("username")
        idms_user_id = attr.get("idms_user_id")
        admin_email = attr.get("admin_email")
        root = User.objects.filter(idms_user_id=idms_user_id).exclude(
            username=user_name
        )
        if root.exists():
            raise serializers.ValidationError(
                _(f"idms is already taken by another admin.")
            )

        _root = User.objects.filter(email=admin_email).exclude(username=user_name)
        if _root.exists():
            raise serializers.ValidationError(
                _(f"email is already taken by another admin.")
            )
        return attr


class Merchantserializer(serializers.Serializer):

    username = serializers.CharField(max_length=100, required=True)
    mobile_number = serializers.CharField(max_length=100, required=True)

    email = serializers.EmailField(max_length=100, required=False)
    idms_user_id = serializers.CharField(max_length=100, required=True)

    def validate(self, attr):

        is_required_msg = "This field is required"

        if not attr.get("username"):
            raise serializers.ValidationError(_(f"username {is_required_msg}"))
        if not attr.get("mobile_number"):
            raise serializers.ValidationError(_(f"mobile_number {is_required_msg}"))
        if not attr.get("idms_user_id"):
            raise serializers.ValidationError(_(f"idms_user_id {is_required_msg}"))

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
