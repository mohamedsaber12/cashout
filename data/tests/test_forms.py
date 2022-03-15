from users.tests.factories import SuperAdminUserFactory
from data.forms import FileDocumentForm, FileCategoryForm
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile



from rest_framework.test import APITestCase
from users.tests.factories import SuperAdminUserFactory, AdminUserFactory
from data.tests.factories import DisbursementFileCategoryFactory
from users.models import EntitySetup


class Request:
    def __init__(self, user):
        self.user = user
        

class TestFileDocumentForm(APITestCase):
                
    # test new_amount validation
    def test_validate_form(self):
        im = Image.new(mode='RGB', size=(200, 200))
        im_io = BytesIO()
        im.save(im_io, 'JPEG')
        im_io.seek(0)

        file = InMemoryUploadedFile(
            im_io, None, 'random-name.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', len(im_io.getvalue()), None
        )
        file_doc_form = FileDocumentForm(
            data={"file": file},
            request={"test": "test"}
        )
        self.assertEqual(file_doc_form.is_valid(), False)
           
    def test_validate_file_type(self):
        im = Image.new(mode='RGB', size=(200, 200))
        im_io = BytesIO()
        im.save(im_io, 'JPEG')
        im_io.seek(0)

        file = InMemoryUploadedFile(
            im_io, None, 'random-name.jpg', 'image/jpeg', len(im_io.getvalue()), None
        )
        file_doc_form = FileDocumentForm(
            data={"file": file},
            request={"test": "test"}
        )
        self.assertEqual(file_doc_form._validate_file_type(file), ('jpeg', 'File type is not supported. Supported types are .xls or .xlsx'))
        
    def test_validate_file_name_right_name(self):
        im = Image.new(mode='RGB', size=(200, 200))
        im_io = BytesIO()
        im.save(im_io, 'JPEG')
        im_io.seek(0)

        file = InMemoryUploadedFile(
            im_io, None, 'random-name.jpg', 'image/jpeg', len(im_io.getvalue()), None
        )
        file_doc_form = FileDocumentForm(
            data={"file": file},
            request={"test": "test"}
        )
        self.assertEqual(file_doc_form._validate_file_name(file), ('random-name', False))
        
    def test_validate_file_name_special_character(self):
        im = Image.new(mode='RGB', size=(200, 200))
        im_io = BytesIO()
        im.save(im_io, 'JPEG')
        im_io.seek(0)

        file = InMemoryUploadedFile(
            im_io, None, 'random*name.jpg', 'image/jpeg', len(im_io.getvalue()), None
        )
        file_doc_form = FileDocumentForm(
            data={"file": file},
            request={"test": "test"}
        )
        self.assertEqual(file_doc_form._validate_file_name(file), ('random*name', 'Filename should not include any unicode characters ex: >, <, /, $, * '))
        
    def test_validate_file_name_long_name(self):
        im = Image.new(mode='RGB', size=(200, 200))
        im_io = BytesIO()
        im.save(im_io, 'JPEG')
        im_io.seek(0)

        file = InMemoryUploadedFile(
            im_io, None, 'AEnPAZGByZWikhPNUtQRLvGjOdBuqxuXLbGIAXGANzQOiUNDBKAEnPAZGByZWikhPNUtQRLvGjOdBuqxuXLbGIAXGANzQOiUNDBKAEnPAZGByZWikhPNUtQRLvGjOdBuqxuXLbGIAXGANzQOiUNDBK.jpg', 'image/jpeg', len(im_io.getvalue()), None
        )
        file_doc_form = FileDocumentForm(
            data={"file": file},
            request={"test": "test"}
        )
        self.assertEqual(file_doc_form._validate_file_name(file), ('AEnPAZGByZWikhPNUtQRLvGjOdBuqxuXLbGIAXGANzQOiUNDBKAEnPAZGByZWikhPNUtQRLvGjOdBuqxuXLbGIAXGANzQOiUNDBKAEnPAZGByZWikhPNUtQRLvGjOdBuqxuXLbGIAXGANzQOiUNDBK', 'Filename must be less than 100 characters'))
        
    def test_validate_file_size(self):
        im = Image.new(mode='RGB', size=(200, 200))
        im_io = BytesIO()
        im.save(im_io, 'JPEG')
        im_io.seek(0)

        file = InMemoryUploadedFile(
            im_io, None, 'random-name.jpg', 'image/jpeg', len(im_io.getvalue()), None
        )
        file_doc_form = FileDocumentForm(
            data={"file": file},
            request={"test": "test"}
        )
        self.assertEqual(file_doc_form._validate_file_size(file), (1303, False))
        
    def test_write_to_disk_e_wallets(self):
        im = Image.new(mode='RGB', size=(200, 200))
        im_io = BytesIO()
        im.save(im_io, 'JPEG')
        im_io.seek(0)

        file = InMemoryUploadedFile(
            im_io, None, 'random-name.xlsx', 'image/jpeg', len(im_io.getvalue()), None
        )
        file_doc_form = FileDocumentForm(
            data={"file": file},
            request=Request(SuperAdminUserFactory()),
            doc_type=1
        )
        file_cat = DisbursementFileCategoryFactory()
        with self.assertRaises(Exception):
            file_doc_form.write_file_to_disk(file, file_cat)
        
    def test_write_to_disk_bank_card(self):
        im = Image.new(mode='RGB', size=(200, 200))
        im_io = BytesIO()
        im.save(im_io, 'JPEG')
        im_io.seek(0)

        file = InMemoryUploadedFile(
            im_io, None, 'random-name.xlsx', 'image/jpeg', len(im_io.getvalue()), None
        )
        file_doc_form = FileDocumentForm(
            data={"file": file},
            request=Request(SuperAdminUserFactory()),
            doc_type=3
        )
        file_cat = DisbursementFileCategoryFactory()
        with self.assertRaises(Exception):
            file_doc_form.write_file_to_disk(file, file_cat)
        
    def test_write_to_disk_bank_wallet(self):
        im = Image.new(mode='RGB', size=(200, 200))
        im_io = BytesIO()
        im.save(im_io, 'JPEG')
        im_io.seek(0)

        file = InMemoryUploadedFile(
            im_io, None, 'random-name.xlsx', 'image/jpeg', len(im_io.getvalue()), None
        )
        file_doc_form = FileDocumentForm(
            data={"file": file},
            request=Request(SuperAdminUserFactory()),
            doc_type=4
        )
        file_cat = DisbursementFileCategoryFactory()
        with self.assertRaises(Exception):
            file_doc_form.write_file_to_disk(file, file_cat)
            
    def test_clean_file(self):
        im = Image.new(mode='RGB', size=(200, 200))
        im_io = BytesIO()
        im.save(im_io, 'JPEG')
        im_io.seek(0)

        file = InMemoryUploadedFile(
            im_io, None, 'random-name.xlsx', 'image/jpeg', len(im_io.getvalue()), None
        )
        file_doc_form = FileDocumentForm(
            data={"file": file},
            request=Request(SuperAdminUserFactory()),
            doc_type=4,
        )
        file_doc_form.cleaned_data = {"file": file}
        with self.assertRaises(Exception):
            file_doc_form.clean_file()        


class TestFileCategoryForm(APITestCase):
                
    # test new_amount validation
    def test_validate_form(self):
        root = AdminUserFactory(user_type=3, hierarchy=90)
        DisbursementFileCategoryFactory(user_created=root)
        EntitySetup(entity=root)
        file_doc_form = FileCategoryForm(
            data={"test": "test"},
            request=Request(root),
        )
        self.assertEqual(file_doc_form.is_valid(), False)
        
    def test_validate_form_with_no_request_and_instance(self):
        root = AdminUserFactory(user_type=3, hierarchy=90)
        inst = DisbursementFileCategoryFactory(user_created=root)
        EntitySetup(entity=root)
        file_doc_form = FileCategoryForm(
            data={"test": "test"},
            instance=inst,
        )
        self.assertEqual(file_doc_form.is_valid(), False)

        
    def test_clean_name(self):
        root = AdminUserFactory(user_type=3, hierarchy=90)
        inst = DisbursementFileCategoryFactory(user_created=root)
        EntitySetup(entity=root)
        file_doc_form = FileCategoryForm(
            data={"name": "test"},
            request=Request(root),
            instance=inst
        )
        file_doc_form.is_valid()
        self.assertEqual(file_doc_form.clean_name(), "test")
        
    # def test_clean_no_of_reviews_required(self):
    #     root = AdminUserFactory(user_type=3, hierarchy=90)
    #     inst = DisbursementFileCategoryFactory(user_created=root)
    #     EntitySetup(entity=root)
    #     form_data = {"no_of_reviews_required": 2}
    #     file_doc_form = FileCategoryForm(
    #         data=form_data,
    #         request=Request(root),
    #         instance=inst
    #     )
    #     file_doc_form.is_valid()
    #     self.assertEqual(file_doc_form.clean_no_of_reviews_required(), "test")
        
    def test_clean(self):
        root = AdminUserFactory(user_type=3, hierarchy=90)
        inst = DisbursementFileCategoryFactory(user_created=root)
        EntitySetup(entity=root)
        form_data = {"unique_field": "A-1", "amount_field": "B-1", "issuer_field": "C-1"}
        file_doc_form = FileCategoryForm(
            data=form_data,
            request=Request(root),
            instance=inst
        )
        file_doc_form.is_valid()
        self.assertEqual(file_doc_form.clean(), {'unique_field': 'A-1', 'amount_field': 'B-1'})
        
    def test_clean_bad_headers(self):
        root = AdminUserFactory(user_type=3, hierarchy=90)
        inst = DisbursementFileCategoryFactory(user_created=root)
        EntitySetup(entity=root)
        form_data = {"unique_field": "A-a", "amount_field": "B-b", "issuer_field": "C-c"}
        file_doc_form = FileCategoryForm(
            data=form_data,
            request=Request(root),
            instance=inst
        )
        self.assertEqual(file_doc_form.is_valid(), False)
        
    def test_clean_not_same_rows(self):
        root = AdminUserFactory(user_type=3, hierarchy=90)
        inst = DisbursementFileCategoryFactory(user_created=root)
        EntitySetup(entity=root)
        form_data = {"unique_field": "A-1", "amount_field": "B-2", "issuer_field": "C-3"}
        file_doc_form = FileCategoryForm(
            data=form_data,
            request=Request(root),
            instance=inst
        )
        self.assertEqual(file_doc_form.is_valid(), False)
        
        
    def test_clean_not_same_col(self):
        root = AdminUserFactory(user_type=3, hierarchy=90)
        inst = DisbursementFileCategoryFactory(user_created=root)
        EntitySetup(entity=root)
        form_data = {"unique_field": "A-1", "amount_field": "A-1"}
        file_doc_form = FileCategoryForm(
            data=form_data,
            request=Request(root),
            instance=inst
        )
        self.assertEqual(file_doc_form.is_valid(), False)
        
    def test_clean_bad_headers_not_normal_flow(self):
        root = AdminUserFactory(user_type=3, hierarchy=90)
        inst = DisbursementFileCategoryFactory(user_created=root)
        EntitySetup(entity=root, is_normal_flow=False)
        form_data = {"unique_field": "A-a", "amount_field": "B-b", "issuer_field": "C-c"}
        file_doc_form = FileCategoryForm(
            data=form_data,
            request=Request(root),
            instance=inst
        )
        self.assertEqual(file_doc_form.is_valid(), False)
        
    def test_clean_not_same_rows_not_normal_flow(self):
        root = AdminUserFactory(user_type=3, hierarchy=90)
        inst = DisbursementFileCategoryFactory(user_created=root)
        EntitySetup(entity=root, is_normal_flow=False)
        form_data = {"unique_field": "A-1", "amount_field": "B-2", "issuer_field": "C-3"}
        file_doc_form = FileCategoryForm(
            data=form_data,
            request=Request(root),
            instance=inst
        )
        self.assertEqual(file_doc_form.is_valid(), False)
        
    def test_clean_not_same_col_not_normal_flow(self):
        root = AdminUserFactory(user_type=3, hierarchy=90)
        inst = DisbursementFileCategoryFactory(user_created=root)
        EntitySetup(entity=root, is_normal_flow=False)
        form_data = {"unique_field": "A-1", "amount_field": "A-1", "issuer_field": "A-1"}
        file_doc_form = FileCategoryForm(
            data=form_data,
            request=Request(root),
            instance=inst
        )
        self.assertEqual(file_doc_form.is_valid(), False)

        
                
    def test_clean_not_normal_flow(self):
        root = AdminUserFactory(user_type=3, hierarchy=90)
        inst = DisbursementFileCategoryFactory(user_created=root)
        EntitySetup(entity=root, is_normal_flow=False)
        form_data = {"unique_field": "A-1", "amount_field": "B-1", "issuer_field": "C-1"}
        file_doc_form = FileCategoryForm(
            data=form_data,
            request=Request(root),
            instance=inst
        )
        file_doc_form.is_valid()
        self.assertEqual(file_doc_form.clean(), {'unique_field': 'A-1', 'amount_field': 'B-1', 'issuer_field': 'C-1'})
        
    def test_clean_no_of_reviews_required(self):
        root = AdminUserFactory(user_type=3, hierarchy=90)
        AdminUserFactory(user_type=2, hierarchy=90)
        inst = DisbursementFileCategoryFactory(user_created=root)
        EntitySetup(entity=root)
        form_data = {"unique_field": "A-1", "amount_field": "B-1", "issuer_field": "C-1", "no_of_reviews_required": 1, "name": "test2"}
        file_doc_form = FileCategoryForm(
            data=form_data,
            request=Request(root),
            instance=inst
        )
        file_doc_form.is_valid()
        self.assertEqual(file_doc_form.clean_no_of_reviews_required(), 1)
          
    def test_clean_no_of_reviews_required_zero(self):
        root = AdminUserFactory(user_type=3, hierarchy=90)
        AdminUserFactory(user_type=2, hierarchy=90)
        inst = DisbursementFileCategoryFactory(user_created=root)
        EntitySetup(entity=root)
        form_data = {"unique_field": "A-1", "amount_field": "B-1", "issuer_field": "C-1", "no_of_reviews_required": 0, "name": "test2"}
        file_doc_form = FileCategoryForm(
            data=form_data,
            request=Request(root),
            instance=inst
        )
        file_doc_form.is_valid()
        self.assertEqual(file_doc_form.errors["no_of_reviews_required"][0], "Number of reviews must be greater than zero")
        
    def test_clean_no_of_reviews_required_more_than_checkers(self):
        root = AdminUserFactory(user_type=3, hierarchy=90)
        AdminUserFactory(user_type=2, hierarchy=90)
        inst = DisbursementFileCategoryFactory(user_created=root)
        EntitySetup(entity=root)
        form_data = {"unique_field": "A-1", "amount_field": "B-1", "issuer_field": "C-1", "no_of_reviews_required": 2, "name": "test2"}
        file_doc_form = FileCategoryForm(
            data=form_data,
            request=Request(root),
            instance=inst
        )
        file_doc_form.is_valid()
        self.assertEqual(file_doc_form.errors["no_of_reviews_required"][0], "Number of reviews must be less than or equal the number of checkers")


