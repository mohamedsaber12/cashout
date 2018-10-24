from users.models.base_user import UserManager, User


class CheckerManager(UserManager):
    def get_queryset(self):
        return super(CheckerManager, self).get_queryset().filter(
            user_type=2)

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('user_type', 2)
        extra_fields.setdefault('is_superuser', False)
        if 'hierarchy' not in extra_fields:
            raise ValueError('The given hierarchy must be set')
        return self._create_user(username, email, password, **extra_fields)


class CheckerUser(User):
    objects = CheckerManager()

    class Meta:
        proxy = True

