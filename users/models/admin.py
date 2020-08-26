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

    def first_non_super_agent(self, wallet_issuer=None):
        """
        Return the first non super agent to be used at the instant disbursement
        :param wallet_issuer: type of the passed wallet issuer
        :return: the first non super agent or None
        """
        msisdn_issuer_type = "E" if wallet_issuer == "ETISALAT" else "V"

        if self.agents:
            qs = self.agents.filter(super=False, type=msisdn_issuer_type)
            if qs.count() > 0:
                return qs.first().msisdn

        raise ValueError(f"{self.username} root/wallet_issuer has no agents setup.")
