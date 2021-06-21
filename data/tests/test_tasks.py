from django.test import TestCase
from data.tasks import BankWalletsAndCardsSheetProcessor
from data.tests.factories import DocFactory
from users.tests.factories import MakerUserFactory
from unittest import mock
from disbursement.factories import DisbursementDocDataFactory



class TestBankWalletsAndCardsSheetProcessor(TestCase):
    
    @mock.patch("users.signals.notify_user")
    def setUp(self, mocked_notify_user):
        self.maker = MakerUserFactory()
        self.doc = DocFactory(owner=self.maker)
        self.disb_trn = DisbursementDocDataFactory(doc=self.doc)
        
        
    @mock.patch("users.signals.notify_user")  
    def test_amount_is_valid_digit_good_number(self, mocked_notify_user):
        obj = BankWalletsAndCardsSheetProcessor(self.doc.id)
        resp = obj.amount_is_valid_digit("ki")
        print(resp)
        
        