from users.tests.factories import SuperAdminUserFactory, CheckerUserFactory
from django.test import TestCase
from data.tests.factories import FormarFactory, FileDataFactory, DocFactory
from data.models.category_data import Format
from data.models.file_data import FileData
from unittest import mock


class TestModelCategoryData(TestCase):
    def setUp(self):
        self.format1 = FormarFactory()
        self.format2 = FormarFactory()
        
    def test_create_format(self):
        formats = Format.objects.all()
        self.assertEqual(formats.count(), 2)
        
    def test_identifiers_function(self):
        identifiers = self.format1.identifiers()
        self.assertEqual(identifiers, [self.format1.identifier1, self.format1.identifier2,self.format1.identifier3, self.format1.identifier4, self.format1.identifier5, self.format1.identifier6, self.format1.identifier7, self.format1.identifier8, self.format1.identifier9, self.format1.identifier10])
        
    def test_headers_match_function(self):
        headers = self.format1.identifiers()
        resp = self.format1.headers_match(headers)
        self.assertTrue(resp)
             
class TestModelFileData(TestCase):
    
    def setUp(self):
        self.super_user = SuperAdminUserFactory()
        self.doc = DocFactory(owner=self.super_user, disbursed_by=self.super_user)
        self.file_data1 = FileDataFactory(user=self.super_user, doc=self.doc)
        self.file_data2 = FileDataFactory(user=self.super_user)
        
        
    def test_str_name(self):
        self.assertEqual(self.file_data1.__str__(), "Data")
        
    def test_doc_name(self):
        self.assertEqual(self.file_data2.doc_name(), "Data")
        
    def test_unicode_name(self):
        self.assertEqual(self.file_data1.__unicode__(), "Data")
        
    def test_search_file_data(self):
        resp = FileData.objects.search_file_data(self.doc, self.doc.txn_id)
        self.assertEqual(resp.first(), self.file_data1)
        
    @mock.patch("users.signals.notify_user")  
    def test_transactions_in_range(self, mocked_notify_user):
        checker = CheckerUserFactory()
        resp = FileData.objects.transactions_in_range(checker)
        self.assertEqual(list(resp), [])
   
    @mock.patch("users.signals.notify_user")  
    def test_unseen_transactions(self, mocked_notify_user):
        checker = CheckerUserFactory()
        resp = FileData.objects.unseen_transactions(checker)
        self.assertEqual(list(resp), [])
        
