from .base_user import User, UserManager


class RootManager(UserManager):
    """
    Manager for the Admin/Root user
    """
    def get_queryset(self):
        return super(RootManager, self).get_queryset().filter(user_type=3)

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('user_type', 3)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(username, email, password, **extra_fields)


class RootUser(User):
    """
    Admin user is the parent who starts to create children (Maker, Checker, Instant, etc.)
    """
    objects = RootManager()

    class Meta:
        proxy = True
