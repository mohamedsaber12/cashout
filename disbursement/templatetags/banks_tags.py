# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import template
from django.utils.translation import ugettext_lazy as _

register = template.Library()


@register.filter
def bank_name(code):
    """Map bank name regarding corresponding bank code"""

    if code == 'AUB':
        return _('Ahli United Bank')
    elif code == 'CITI':
        return _('Citi Bank N.A. Egypt')
    elif code == 'MIDB':
        return _('MIDBANK')
    elif code == 'BDC':
        return _('Banque Du Caire')
    elif code == 'HSBC':
        return _('HSBC Bank Egypt S.A.E')
    elif code == 'CAE':
        return _('Credit Agricole Egypt S.A.E')
    elif code == 'EGB':
        return _('Egyptian Gulf Bank')
    elif code == 'UB':
        return _('The United Bank')
    elif code == 'QNB':
        return _('Qatar National Bank Alahli')
    elif code == 'BBE':
        return _('Central Bank Of Egypt')
    elif code == 'ARAB':
        return _('Arab Bank PLC')
    elif code == 'ENBD':
        return _('Emirates National Bank of Dubai')
    elif code == 'ABK':
        return _('Al Ahli Bank of Kuwait – Egypt')
    elif code == 'NBK':
        return _('National Bank of Kuwait – Egypt')
    elif code == 'ABC':
        return _('Arab Banking Corporation - Egypt S.A.E')
    elif code == 'FAB':
        return _('First Abu Dhabi Bank')
    elif code == 'ADIB':
        return _('Abu Dhabi Islamic Bank – Egypt')
    elif code == 'CIB':
        return _('Commercial International Bank - Egypt S.A.E')
    elif code == 'HDB':
        return _('Housing And Development Bank')
    elif code == 'MISR':
        return _('Banque Misr')
    elif code == 'AAIB':
        return _('Arab African International Bank')
    elif code == 'EALB':
        return _('Egyptian Arab Land Bank')
    elif code == 'EDBE':
        return _('Export Development Bank of Egypt')
    elif code == 'FAIB':
        return _('Faisal Islamic Bank of Egypt')
    elif code == 'BLOM':
        return _('Blom Bank')
    elif code == 'ADCB':
        return _('Abu Dhabi Commercial Bank – Egypt')
    elif code == 'BOA':
        return _('Alex Bank Egypt')
    elif code == 'SAIB':
        return _('Societe Arabe Internationale De Banque')
    elif code == 'NBE':
        return _('National Bank of Egypt')
    elif code == 'ABRK':
        return _('Al Baraka Bank Egypt B.S.C.')
    elif code == 'POST':
        return _('Egypt Post')
    elif code == 'NSB':
        return _('Nasser Social Bank')
    elif code == 'IDB':
        return _('Industrial Development Bank')
    elif code == 'SCB':
        return _('Suez Canal Bank')
    elif code == 'MASH':
        return _('Mashreq Bank')
    elif code == 'AIB':
        return _('Arab Investment Bank')
    elif code == 'AUDI':
        return _('Audi Bank')
    elif code == 'GASC':
        return _('General Authority For Supply Commodities')
    elif code == 'EGPA':
        return _('National Bank of Egypt - EGPA')
    elif code == 'ARIB':
        return _('Arab International Bank')
    elif code == 'PDAC':
        return _('Agricultural Bank of Egypt')
    elif code == 'NBG':
        return _('National Bank of Greece')
    elif code == 'CBE':
        return _('Central Bank Of Egypt')
    else:
        return ''
