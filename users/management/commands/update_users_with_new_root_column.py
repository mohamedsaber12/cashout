from django.core.management.base import BaseCommand, CommandError
from users.models import  RootUser, User

class Command(BaseCommand):
    help = "this command exist for update users table in db with root column"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('start getting users from db ...'))
        # get all users with types (maker, checkers, InstantAPIChecker, InstantAPIViewer, root)
        current_users = User.objects.filter(user_type__in=[1, 2, 6, 7, 3])

        self.stdout.write(self.style.SUCCESS('finish getting users'))

        self.stdout.write(self.style.SUCCESS('start updating users with root ...'))
        self.stdout.write(self.style.SUCCESS('----------------------------------------'))

        for current_user in current_users:
            # get root of current user
            current_root = None
            try:
                if current_user.is_root:
                    current_root = current_user
                else:
                    current_root = RootUser.objects.get(hierarchy=current_user.hierarchy)
            except User.DoesNotExist:
                raise CommandError('Root of this user "%s" does not exist' % current_user)

            # update each user with his root
            current_user.root = current_root
            current_user.save()
            self.stdout.write(
                self.style.SUCCESS(f"{current_user} updated successfully with root {current_root}")
            )

        self.stdout.write(self.style.SUCCESS('----------------------------------------'))
        self.stdout.write(self.style.SUCCESS('finish updating users with root'))
