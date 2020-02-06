from django.db.models import Q

from .base_user import User, UserManager


class MakerManager(UserManager):
    """
    Manager for the Maker user
    """
    def get_queryset(self):
        return super(MakerManager, self).get_queryset().filter(
            Q(user_type=1) |
            Q(user_type=5)
        )

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('user_type', 1)
        extra_fields.setdefault('is_superuser', False)
        if 'hierarchy' not in extra_fields:
            raise ValueError('The given hierarchy must be set')
        return self._create_user(username, email, password, **extra_fields)


class MakerUser(User):
    """
    Maker user who uploads a file to be reviewed and disbursed by his same hierarchy levels of checkers
    """
    objects = MakerManager()

    class Meta:
        proxy = True
