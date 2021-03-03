from django.core.management.base import BaseCommand
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
        users_with_no_root = []
        users_have_root_count = 0
        for current_user in current_users:
            # get root of current user
            try:
                if current_user.is_root:
                    current_root = current_user
                else:
                    current_root = RootUser.objects.get(hierarchy=current_user.hierarchy)
                users_have_root_count += 1
            except User.DoesNotExist:
                users_with_no_root.append(current_user)
                self.stdout.write(
                    self.style.ERROR(
                        'Error:-  Root of this user ==> "%s" does not exist' % current_user
                    )
                )
            else:
                # update each user with his root
                current_user.root = current_root
                current_user.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{current_user} updated successfully with root {current_root}"
                    )
                )

        self.stdout.write(self.style.SUCCESS('----------------------------------------'))
        self.stdout.write(self.style.SUCCESS('finish updating users with root'))
        self.stdout.write(self.style.SUCCESS('=========== Summary ==========='))

        self.stdout.write(
            self.style.SUCCESS(f"Number of Updated Users is : {users_have_root_count}")
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Number of Users that have no root is : {len(users_with_no_root)}")
        )
        # print users with no root
        self.stdout.write(self.style.SUCCESS(f"Users With no root :- "))
        for u in users_with_no_root:
            self.stdout.write(self.style.SUCCESS(f"user ==> {u}, with id ==> {u.id}"))
        if len(users_with_no_root) == 0:
            self.stdout.write(self.style.SUCCESS(f"[]"))