from .base_user import User, UserManager


class InstantAPICheckerManager(UserManager):
    """
    Manager for the Instant API Checker user
    """
    def get_queryset(self):
        return super().get_queryset().filter(user_type=6)

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('user_type', 6)
        extra_fields.setdefault('is_superuser', False)
        if 'hierarchy' not in extra_fields:
            raise ValueError('The given hierarchy must be set')
        return self._create_user(username, email, password, **extra_fields)


class InstantAPICheckerUser(User):
    """
    Instant API Checker user who can disburse instantly through and API endpoint
    """
    objects = InstantAPICheckerManager()

    class Meta:
        proxy = True
