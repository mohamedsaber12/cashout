from .base_user import User, UserManager


class AdminManager(UserManager):
    """
    Manager for the SuperAdmin user
    """
    def get_queryset(self):
        return super(AdminManager, self).get_queryset().filter(user_type=0)

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('user_type', 0)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(username, email, password, **extra_fields)


class SuperAdminUser(User):
    """
    SuperAdmin user who starts/manages the chain/process
    """
    objects = AdminManager()

    class Meta:
        proxy = True
