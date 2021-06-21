from abc import abstractmethod

from generics.auth.helpers import LoggedInUser


class BasicAuthenticatorMixin(object):
    """
    class used to add authentication related functionality to test cases.
    includes behavior such as logging in and logging out using a username and password
    """

    _logged_in_user = LoggedInUser()

    @property
    def logged_in_user(self):
        return self._logged_in_user.user

    @logged_in_user.setter
    def logged_in_user(self, value):
        self._logged_in_user.user = value

    def login(self, client, user, **kwargs):
        b_success = client.login(
            username=kwargs.get("username", ""),
            password=kwargs.get("password", ""),
        )
        if b_success and not self.logged_in_user:
            self._logged_in_user.set_user_without_request(user)

    def logout(self, client):
        client.logout()
        self.logged_in_user = None


class AbstractUsersCreator(object):
    """
    interface that provides abstract methods related to user creation and management
    """

    @abstractmethod
    def create_user(self, **kwargs):
        pass
