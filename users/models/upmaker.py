from django.db.models import Q

from .base_user import User, UserManager


class UpmakerManager(UserManager):
    def get_queryset(self):
        return super().get_queryset().filter(
            Q(user_type=5)
        )

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('user_type', 5)
        extra_fields.setdefault('is_superuser', False)
        if 'hierarchy' not in extra_fields:
            raise ValueError('The given hierarchy must be set')
        return self._create_user(username, email, password, **extra_fields)


class UpmakerUser(User):
    objects = UpmakerManager()

    class Meta:
        proxy = True
