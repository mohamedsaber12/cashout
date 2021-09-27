from instant_cashin.models.instant_transactions import InstantTransaction
from disbursement.models import BankTransaction, DisbursementData
from django.core.management.base import BaseCommand
from django.core.paginator import Paginator
from django.db.models import Q


class Command(BaseCommand):
    help = "this command exist for update disbursement table in db with fees and vat"

    def handle(self, *args, **options):

        # set fees and vat in disbursement record model
        self.stdout.write(self.style.SUCCESS('start getting Disbursement data records page by page...'))
        self.stdout.write(self.style.SUCCESS(''))

        disb_data_records = DisbursementData.objects.all().order_by('-created_at')

        self.stdout.write(self.style.SUCCESS(
            'start updating Disbursement data records with fees and vat ...'
        ))
        self.stdout.write(self.style.SUCCESS(
            '----------------------------------------')
        )
        paginator = Paginator(disb_data_records, 500)
        for page_number in paginator.page_range:
            queryset = paginator.page(page_number)
            for record in queryset:
                if record.doc.owner.root != None and \
                   record.doc.owner.root.has_custom_budget:
                    record.fees, record.vat = \
                        record.doc.owner.root.budget.calculate_fees_and_vat_for_amount(
                            record.amount, record.issuer
                        )
                    # self.stdout.write(self.style.SUCCESS(
                    #         f"issuer => {record.issuer}, fees => {record.fees}, vat ==> {record.vat}"))
                    record.save(update_fields=['fees', 'vat'])
            self.stdout.write(self.style.SUCCESS(
                '----------------------------------------'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'finish updating Disbursement data records for page => {page_number}'
            ))

        # set fees and vat in instant transaction model
        self.stdout.write(self.style.SUCCESS('start getting instant transaction page by page...'))
        self.stdout.write(self.style.SUCCESS(''))

        instant_trx_records = InstantTransaction.objects.all().order_by('-created_at')

        self.stdout.write(self.style.SUCCESS(
            'start updating instant transactions with fees and vat ...'
        ))
        self.stdout.write(self.style.SUCCESS(
            '----------------------------------------')
        )
        paginator = Paginator(instant_trx_records, 500)
        for page_number in paginator.page_range:
            queryset = paginator.page(page_number)
            for record in queryset:
                # get root user
                budget = None
                if record.from_user is not None:
                    budget = record.from_user.root.budget
                else:
                    budget=record.document.owner.root.budget
                # check budget not none
                if budget is None:
                    self.stdout.write(self.style.ERROR(
                        f'budget for {record} in instant trx not exist'
                    ))
                else:
                    record.fees, record.vat = \
                        budget.calculate_fees_and_vat_for_amount(
                            record.amount, record.issuer_type
                        )
                    record.save(update_fields=['fees', 'vat'])
            self.stdout.write(self.style.SUCCESS(
                '----------------------------------------'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'finish updating instant transaction records for page => {page_number}'
            ))


        # set fees and vat in bank transaction model
        self.stdout.write(self.style.SUCCESS('start getting bank transaction page by page...'))
        self.stdout.write(self.style.SUCCESS(''))

        bank_trx_records = BankTransaction.objects.all().order_by('-created_at')

        self.stdout.write(self.style.SUCCESS(
            'start updating bank transactions with fees and vat ...'
        ))
        self.stdout.write(self.style.SUCCESS(
            '----------------------------------------')
        )
        paginator = Paginator(bank_trx_records, 500)
        for page_number in paginator.page_range:
            queryset = paginator.page(page_number)
            for record in queryset:
                # get root user
                budget = None
                if record.user_created is not None:
                    budget = record.user_created.root.budget
                else:
                    budget=record.document.owner.root.budget
                # check budget not none
                if budget is None:
                    self.stdout.write(self.style.ERROR(
                        f'budget for {record} in bank trx not exist'
                    ))
                else:
                    record.fees, record.vat = \
                        budget.calculate_fees_and_vat_for_amount(
                            record.amount, "bank_card"
                        )
                    record.save(update_fields=['fees', 'vat'])
            self.stdout.write(self.style.SUCCESS(
                '----------------------------------------'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'finish updating bank transaction records for page => {page_number}'
            ))
