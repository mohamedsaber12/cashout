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

    def first_non_super_agent(self, wallet_issuer=None):
        """
        Return the first non super agent to be used at the instant disbursement
        :param wallet_issuer: type of the passed wallet issuer
        :return: the first non super agent or None
        """
        msisdn_issuer = '011' if wallet_issuer == 'ETISALAT' else '010'

        if self.agents:
            qs = self.agents.filter(super=False, msisdn__startswith=msisdn_issuer)
            if qs.count() > 0:
                return qs.first().msisdn

        raise ValueError(f"{self.username} root/wallet_issuer has no agents setup.")
