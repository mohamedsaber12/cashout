from .base_user import User, UserManager


class InstantAPIViewerManager(UserManager):
    """
    Manager for the Instant API Viewer user
    """
    def get_queryset(self):
        return super().get_queryset().filter(user_type=7)

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('user_type', 7)
        extra_fields.setdefault('is_superuser', False)
        if 'hierarchy' not in extra_fields:
            raise ValueError('The given hierarchy must be set')
        return self._create_user(username, email, password, **extra_fields)


class InstantAPIViewerUser(User):
    """
    Instant API Viewer user has the ability to search/view all transactions done via his corresponding APIChecker
    """
    objects = InstantAPIViewerManager()

    class Meta:
        proxy = True
