from django.test import TestCase
from data.tasks import BankWalletsAndCardsSheetProcessor
from data.tests.factories import DocFactory
from users.tests.factories import SuperAdminUser
from unittest import mock
from disbursement.factories import DisbursementDocDataFactory



class TestBankWalletsAndCardsSheetProcessor(TestCase):
    
    # @mock.patch("users.signals.notify_user")
    # def setUp(self, mocked_notify_user):
    #     self.maker = MakerUserFactory()
    #     self.doc = DocFactory(owner=self.maker)
    #     self.disb_trn = DisbursementDocDataFactory(doc=self.doc)
        
        
    @mock.patch("users.signals.notify_user") 
    @mock.patch("users.signals.send_random_pass_to_maker") 
    def test_amount_is_valid_digit_good_number(self, mocked_notify_user, tt):
        self.maker = SuperAdminUser()
        self.doc = DocFactory(owner=self.maker)
        self.disb_trn = DisbursementDocDataFactory(doc=self.doc)
        obj = BankWalletsAndCardsSheetProcessor(self.doc.id)
        resp = obj.amount_is_valid_digit("ki")
        print(resp)
        
        