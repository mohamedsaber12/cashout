# from rest_framework import serializers

# from users.models import RootUser
# from users.models import SuperAdminUser


# class BillInquiryRequestSerializer(serializers.Serializer):
#     biller = serializers.SlugRelatedField(queryset=RootUser.objects.all(), slug_field='username')
#     aggregator = serializers.SlugRelatedField(queryset=SuperAdminUser.objects.all(), slug_field='username')
#     bill_reference = serializers.CharField()
#     bill_reference2 = serializers.CharField(allow_null=True, required=False)
