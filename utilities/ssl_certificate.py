# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import base64
import datetime
import logging

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.x509.oid import NameOID

from django.conf import settings
from django.utils.translation import gettext as _


SSL_CERTIFICATE_LOGGER = logging.getLogger('ssl_certificates')


class SSLCertificate:
    """
    Generate private key and use it to generate SSL certificate
    """

    @staticmethod
    def generate_private_key(key_name, key_size):
        """
        Generate private key with given size and name
        :param key_name: name of the to be created private key
        :param key_size: size of the to be created private key
        :return: Key path if the key is generated successfully or False if not
        """
        if not all([key_name, key_size]):
            raise ValueError(_("Key name and size are mandatory parameters."))

        payload = f"Payload: key_name: {key_name} and key_size: {key_size}"

        try:
            key = rsa.generate_private_key(public_exponent=65537, key_size=key_size, backend=default_backend())

            # Write the generated private key to disk
            key_path = f"{settings.MEDIA_ROOT}/certificates/{key_name.split('.')[0]}.pem"
            with open(key_path, 'wb') as f:
                f.write(key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.TraditionalOpenSSL,
                        encryption_algorithm=serialization.NoEncryption(),
                ))

            SSL_CERTIFICATE_LOGGER.debug(
                    f'[message] [PRIVATE KEY - GENERATED SUCCESSFULLY] [anonymous] -- {payload}, Saved at: {key_path}'
            )
            return key_path

        except Exception as e:
            SSL_CERTIFICATE_LOGGER.debug(
                    f'[message] [PRIVATE KEY - GENERATION FAILED] [anonymous] -- {payload}, Error: {e.args}'
            )
            raise ValueError(_(e.args[0]))

    @staticmethod
    def load_private_key(private_key_name):
        """
        :param private_key_name: private key name to be returned
        :return: valid private key
        """
        try:
            private_key_name = private_key_name.split('.')[0]
            private_key = f"{settings.MEDIA_ROOT}/certificates/{private_key_name}.pem"

            with open(private_key, 'rb') as pem_key:
                pem_key_lines = pem_key.read()

            private_key = load_pem_private_key(pem_key_lines, None, default_backend())
            return private_key

        except ValueError:
            raise ValueError(_('Provided private key name is not valid'))
        except FileNotFoundError:
            raise FileNotFoundError(_(f'No private key found with the name: {private_key_name}'))

    @staticmethod
    def generate_certificate(private_key_name, cert_name, expiration_period_in_days, organization_name, domain_name):
        """
        Generate ssl certificate using existing private key
        :param private_key_name: private key name that'll be used to generate the certificate from it public key
        :param cert_name: name of the to be generated certificate
        :param expiration_period_in_days: expiration period of the certificate
        :param organization_name: organization name the will be signed at the certificate
        :param domain_name: domain name of the organization
        :return: Generated certificate path or False if any exception is raised
        """
        if not all([private_key_name, cert_name, expiration_period_in_days, organization_name, domain_name]):
            raise ValueError(_('Fields provided are not in a proper format'))

        payload = f"Payload: private_key_name: {private_key_name}, certificate_name: {cert_name}, " + \
                  f"organization_name: {organization_name}, domain_name: {domain_name}, " + \
                  "expiration_period: {expiration_period_in_days}\n"

        try:
            private_key = SSLCertificate.load_private_key(private_key_name)
        except (ValueError, FileNotFoundError) as e:
            SSL_CERTIFICATE_LOGGER.debug(
                    f'[message] [CERTIFICATE - GENERATION FAILED] [anonymous] -- {payload}, Errors: {e.args}'
            )
            return False

        try:
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, u'EG'),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u'Cairo'),
                x509.NameAttribute(NameOID.LOCALITY_NAME, u'Cairo'),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization_name),
                x509.NameAttribute(NameOID.COMMON_NAME, organization_name),
            ])

            ssl_cert = x509.CertificateBuilder().subject_name(
                    subject
            ).issuer_name(
                    issuer
            ).public_key(
                    private_key.public_key()
            ).serial_number(
                    x509.random_serial_number()
            ).not_valid_before(
                    datetime.datetime.utcnow()
            ).not_valid_after(
                    datetime.datetime.utcnow() + datetime.timedelta(days=int(expiration_period_in_days))
            ).add_extension(
                    x509.SubjectAlternativeName([x509.DNSName(domain_name)]), critical=False,
            ).sign(
                    # Sign our certificate with our private key
                    private_key, hashes.SHA256(), default_backend()
            )

            # Write the generated ssl certificate to disk
            cert_path = f"{settings.MEDIA_ROOT}/certificates/{cert_name}.crt"
            with open(cert_path, 'wb') as f:
                f.write(ssl_cert.public_bytes(serialization.Encoding.PEM))

            SSL_CERTIFICATE_LOGGER.debug(
                    f'[message] [SSL CERTIFICATE - GENERATED SUCCESSFULLY] [anonymous] '
                    f'-- {payload}, Saved at: {cert_path}'
            )
            return cert_path

        except Exception as e:
            SSL_CERTIFICATE_LOGGER.debug(
                    f'[message] [SSL CERTIFICATE - GENERATION FAILED] [anonymous] -- {payload}, Errors: {e.args}'
            )
            return False

    @staticmethod
    def generate_signature(private_key_name, payload_without_signature):
        """
        Generate signature for request payload using specific private key
        :param private_key_name:
        :param payload_without_signature: request payload with signature field as json_payload.encode('utf-16')
        :return: signature
        """
        import json
        try:
            refined_key_name = private_key_name.split('.')[0]
            key_path = f"{settings.MEDIA_ROOT}/certificates/{refined_key_name}.pem"

            with open(key_path, 'r') as f:
                private_key_file = f.read()
                private_key_rsa = RSA.importKey(private_key_file)
            
            json_payload_obj = json.loads(payload_without_signature)
            json_payload_obj["TransactionAmount"] = format(json_payload_obj["TransactionAmount"],'.4f')
            updated_payload = json.dumps(json_payload_obj, separators=(",", ":"))
            print(updated_payload)
            hashed_data = SHA256.new(updated_payload.encode('utf-16le'))
            signer = PKCS1_v1_5.new(private_key_rsa).sign(hashed_data)
            return base64.b64encode(signer).decode('utf-8')

        except ValueError:
            raise ValueError(_(f'Provided private key name is not valid'))
        except FileNotFoundError:
            raise FileNotFoundError(_(f'No private key found with the name: {private_key_name}'))
        except Exception as e:
            return _(f'{e.args[0]}')
