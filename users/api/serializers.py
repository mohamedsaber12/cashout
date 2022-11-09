from rest_framework import serializers
from users.models.base_user import User
class Prtaluserserializer(serializers.Serializer):

    username = serializers.CharField(
        max_length=100,
        required=True
    )
    email=serializers.EmailField(
        max_length=100,
        required=True
    )
    idms_user_id = serializers.CharField(
        max_length=100,
        required=True
    )
   

    def validate(self, attr):
           
        user_name=attr.get("username")
        idms_user_id=attr.get("idms_user_id")
        email=attr.get("email")
        root =User.objects.filter(idms_user_id=idms_user_id).exclude(username=user_name)
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

    

        
        
          
        
