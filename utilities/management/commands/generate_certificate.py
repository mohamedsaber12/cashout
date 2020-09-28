# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import random

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _

from ...ssl_certificate import SSLCertificate


class Command(BaseCommand):
    """
    Generate SSL certificate out of already existing private key
    """

    help = 'Used to generate SSL certificate out of already existing private key'
    requires_migrations_checks = False
    requires_system_checks = False


    def _get_input_value(self, message, default=''):
        raw_value = input(message)

        if default and not raw_value:
            raw_value = default
        elif not default and not raw_value:
            raise CommandError('Please enter a valid input!')

        return raw_value

    def handle(self, *args, **options):

        try:
            pk_name = self._get_input_value('Enter name of a valid private key to be used: ', '')
            SSLCertificate.load_private_key(pk_name)
        except (ValueError, FileNotFoundError) as e:
            return self.stdout.write(self.style.ERROR(_(e.args[0])))

        try:
            default_cert_name = f'cert_{pk_name.split(".")[0]}_{random.randint(1, 1000)}'
            cert_name = self._get_input_value(f'Certificate name [{default_cert_name}]: ', default_cert_name)
            org_name = self._get_input_value('Organization name: ')
            domain_name = self._get_input_value('Domain name: ')
            expiration_period = self._get_input_value('Expiration period in days [365 days]: ', '365')
            path = SSLCertificate.generate_certificate(pk_name, cert_name, expiration_period, org_name, domain_name)
            return self.stdout.write(self.style.SUCCESS(_(
                    f'SSL Certificate generated successfully!\nUsed private key: {pk_name}\n'
                    f'Certificate name: {cert_name}.crt\nOrg. name: {org_name}\nDomain name: {domain_name}\n'
                    f'Expiration period: {expiration_period} days\nSaved at: {path}'
            )))
        except Exception as e:
            return self.stdout.write(self.style.ERROR(_(f'Error: {e.args[0]}')))
