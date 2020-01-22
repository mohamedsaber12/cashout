# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import os

import faker
import mock
import xlsxwriter
from django.core.files import File
from django.test import override_settings
from django.urls import reverse_lazy
from test_plus import APITestCase

from data.factories import DisbursementFileCategory
from data.models import Doc
from data.tasks import handle_disbursement_file
from .factories import VMTDataFactory, AgentFactory
from .models import Agent, DisbursementData
from users.factories import DisbursementUserFactory

fake = faker.Factory.create()


@override_settings(
    MEDIA_ROOT='/tmp',
    DEFAULT_AUTHENTICATION_CLASSES=(
            'rest_framework.authentication.BasicAuthentication',
    )
)
class DisbursementAPITest(APITestCase):
    """
    Test DisburseAPIView disbursement -> api -> views
    """
    def setUp(self):
        self.user = DisbursementUserFactory()
        self.vmt = VMTDataFactory.create(vmt=self.user)
        self.category = DisbursementFileCategory.create(user_created=self.user)
        self.doc = Doc.objects.create(owner=self.user, file_category=self.category)
        self.setUpDoc()
        self.api_url = '/disburse/apmORlUSt8qNdF54/'
        # self.api_url = reverse_lazy('disbursement_api:disburse_api')
        AgentFactory.create_batch(size=10, wallet_provider=self.user)
        self.agents = Agent.objects.filter(wallet_provider=self.user)

    def setUpDoc(self):
        """
        Create document excel disbursement data at the /tmp directory
        :return:
        """
        import tempfile
        filename = tempfile.mkstemp(suffix='.xlsx')[1]

        excelFile = xlsxwriter.Workbook(filename=filename)
        worksheet = excelFile.add_worksheet()
        worksheet.set_column(0, 2, width=15)
        worksheet.write('A1', 'MSISDN')
        worksheet.write('B1', 'Amount')
        worksheet.write('C1', 'Name')
        # Start from the first cell. Rows and columns are zero indexed.
        row = 1
        col = 0

        # Iterate over the data and write it out row by row.
        xcl_data = [
            (u'01273551124', 1.0, fake.name()),
            (u'01001001024', 2.0, fake.name()),
            (u'01000972700', 3.0, fake.name()),
            (u'01002222805', 4.0, fake.name()),
            (u'01273551125', 5.0, fake.name()),
            (u'01273551126', 6.0, fake.name()),
            (u'01273551127', 7.0, fake.name()),
            (u'01002222807', 8.0, fake.name()),
            (u'01002222808', 9.0, fake.name()),
            (u'01002222809', 10.0, fake.name())
        ]
        for row_data in xcl_data:
            for data in row_data:
                worksheet.write(row, col, data)
                col += 1
            row += 1
            col = 0
        excelFile.close()
        self.file = filename
        self.doc.file.save(
                name=filename,
                content=File(open(filename))
            )

    def test_handling_disbursement_data_from_docs(self):
        """
        asserts that document created due to file category identifiers can be processed
        and disbursement data are created through `handle_disbursement_file` task
        :return:
        """
        result = handle_disbursement_file(self.doc.id, self.category.id)
        self.assertTrue(result)
        self.assertEqual(self.doc.disbursement_data.count(), 10)

    def test_data_sent_UIG(self):
        """
        Asserts that data sent to uig is right
        :return:
        """
        senders = self.agents.extra(select={'MSISDN': 'msisdn'}).values('MSISDN')
        senders = list(senders)
        for d in senders:
            d.update({'PIN': '123456'})
        recepients = DisbursementData.objects.select_related('doc').filter(doc_id=self.doc.id). \
            extra(select={'MSISDN': 'msisdn', 'AMOUNT': 'amount', 'TXNID': 'id'}).values('MSISDN', 'AMOUNT', 'TXNID')

        data = self.vmt.return_vmt_data()
        data.update({
            "SENDERS": senders,
            "RECIPIENTS": list(recepients),
        })
        self.assertEqual(self.user.agents.count(), 10)
        self.assertEqual(self.user.agents.extra(select={'MSISDN':'msisdn'}).values()[0].has_key('MSISDN'), True)
        self.assertEqual(data.has_key('LOGIN'), True)
        self.assertEqual(data['LOGIN'], self.vmt.login_username)

    @mock.patch('requests.post', return_value=json.dumps({u'BATCH_ID': u'183', u'TXNSTATUS': u'200'}))
    def test_disbursement_api_success(self, req_function):
        self.client.force_authenticate(self.user)
        req_data = {'doc_id': self.doc.id, 'pin': '123456', 'user': self.user.username}
        response = self.post(self.api_url, data=req_data, extra={'format': 'json'})
        self.response_200(response)

    def tearDown(self):
        self.user.delete()
        super(DisbursementAPITest, self).tearDown()
