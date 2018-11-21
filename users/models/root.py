
from users.models.base_user import UserManager, User


class RootManager(UserManager):
    def get_queryset(self):
        return super(RootManager, self).get_queryset().filter(
            user_type=3)

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('user_type', 3)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(username, email, password, **extra_fields)


class RootUser(User):
    objects = RootManager()

    class Meta:
        proxy = True

