from instant_cashin.models.instant_transactions import InstantTransaction
from disbursement.models import BankTransaction, DisbursementData
from django.core.management.base import BaseCommand
from django.db.models import Q


class Command(BaseCommand):
    help = "this command exist for update disburment table in db with updated at"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('start getting Disbursement data records...'))
        disb_data_records = DisbursementData.objects.filter(doc__is_disbursed= True)

        self.stdout.write(self.style.SUCCESS('getting Disbursement data records...'))

        self.stdout.write(self.style.SUCCESS('start updating Disbursement data records with updated at ...'))
        self.stdout.write(self.style.SUCCESS('----------------------------------------'))
        for record in disb_data_records:
           record.disbursed_date = record.updated_at
           record.save(update_fields=['disbursed_date'])
        self.stdout.write(self.style.SUCCESS('----------------------------------------'))
        self.stdout.write(self.style.SUCCESS('finish updating Disbursement data records'))


        self.stdout.write(self.style.SUCCESS('start getting bank transactions records...'))
        bank_transactions_records = BankTransaction.objects.filter(Q(document__is_disbursed= True) | Q(is_single_step=True)| Q(user_created__user_type=6) | ~Q(end_to_end=""))

        self.stdout.write(self.style.SUCCESS('getting bank transactions records...'))

        self.stdout.write(self.style.SUCCESS('start updating bank transactions records with updated at ...'))
        self.stdout.write(self.style.SUCCESS('----------------------------------------'))
        for record in bank_transactions_records:
            date = record.updated_at
            record.disbursed_date = date
            record.save(update_fields=['disbursed_date'])
        self.stdout.write(self.style.SUCCESS('----------------------------------------'))
        self.stdout.write(self.style.SUCCESS('finish updating bank transactions records'))



        self.stdout.write(self.style.SUCCESS('start getting instant transactions records...'))
        single_step_transactions_records = InstantTransaction.objects.filter(Q(document__is_disbursed= True) | Q(is_single_step=True)| Q(from_user__user_type=6))

        self.stdout.write(self.style.SUCCESS('getting instant transactions records...'))

        self.stdout.write(self.style.SUCCESS('start updating instant transactions records with updated at ...'))
        self.stdout.write(self.style.SUCCESS('----------------------------------------'))
        for record in single_step_transactions_records:
            date = record.updated_at
            record.disbursed_date = date
            record.save(update_fields=['disbursed_date'])
        self.stdout.write(self.style.SUCCESS('----------------------------------------'))
        self.stdout.write(self.style.SUCCESS('finish updating instant transactions records'))