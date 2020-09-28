# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import random

from django.core.management.base import BaseCommand, CommandError

from ...ssl_certificate import SSLCertificate


class Command(BaseCommand):
    """
    Generate private key
    """

    help = "Used to generate a private key with custom size"
    requires_migrations_checks = False
    requires_system_checks = False

    def _get_input_value(self, message, default):
        raw_value = input(message)

        if default and not raw_value:
            raw_value = default
        elif not default and not raw_value:
            raise CommandError('Please enter a valid input!')

        return raw_value

    def handle(self, *args, **options):
        default_key_name = f'paymob_{random.randrange(1, 1000)}'

        try:
            key_name = self._get_input_value(f'Key name [{default_key_name}.pem]: ', default=default_key_name)
            key_name = key_name.split('.')[0]
            key_size = self._get_input_value('Key size [2048]: ', default=2048)
            key_path = SSLCertificate.generate_private_key(key_name, int(key_size))
        except Exception as e:
            return self.stdout.write(self.style.ERROR(f'Error: {e.args[0]}'))

        return self.stdout.write(self.style.SUCCESS(
                f'Private key generated successfully!\nName: {key_name}.pem\nSize: {key_size}\nAt: {key_path}')
        )
