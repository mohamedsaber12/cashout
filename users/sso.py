from curses.ascii import US
from django.conf import settings
import requests
from users.models.base_user import User
import logging


SSO_INTEGRATION_LOGGER = logging.getLogger("sso_integration")


class SSOIntegration:
    def register_user_on_idms(self, user):
        SSO_INTEGRATION_LOGGER.debug(
            f"SSO INTEGRATION REGISTER USER ON IDMS User {user}"
        )
        payload = {
            "username": user.username,
            "email": user.email,
        }
        url = f"{settings.IDMS_BASE_URL}accounts/signup/"
        resp = requests.post(url, json=payload)
        SSO_INTEGRATION_LOGGER.debug(
            f"SSO INTEGRATION SEND SIGNUP REQUEST [URL - CONTENT - STATUS_CODE - DELTA]"
            f"[{resp.url}] - [{resp.content}] - [{resp.status_code}] "
            f"- [{resp.elapsed.total_seconds()}]"
        )

        user.idms_user_id = resp.json().get("id")
        user.save()

    def edit_user_on_idms(self, user):
        SSO_INTEGRATION_LOGGER.debug(
            f"SSO INTEGRATION EDIT USER ON IDMS User {user}"
        )
        if user.idms_user_id:
            payload = {
                "username": user.username,
                "email": user.email,
                "phone_number": user.mobile_no,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active":user.is_active
            }
            url = f"{settings.IDMS_BASE_URL}v1/analytics/users/{user.idms_user_id}"
            resp = requests.put(url, json=payload)
            SSO_INTEGRATION_LOGGER.debug(
                f"SSO INTEGRATION EDIT USER ON IDMS REQUEST [URL - CONTENT - STATUS_CODE - DELTA]"
                f"[{resp.url}] - [{resp.content}] - [{resp.status_code}] "
                f"- [{resp.elapsed.total_seconds()}]"
            )
        else:
            SSO_INTEGRATION_LOGGER.debug(
            f"SSO INTEGRATION EDIT USER ON IDMS User {user} FAILED [NO IDMS USER ID ATTACHED]"
        )

    def change_user_password(self, user, password):
        SSO_INTEGRATION_LOGGER.debug(f"SSO INTEGRATION CHANGE USER PASSWORD {user}")
        payload = {"username": user.username, "password": password}
        url = f"{settings.IDMS_BASE_URL}accounts/password/reset/"
        # headers = {"Authorization": f"Bearer {self.create_idms_access_token()}"}
        resp = requests.post(url, json=payload)
        SSO_INTEGRATION_LOGGER.debug(
            f"SSO INTEGRATION RESET PASSWORD REQUEST [URL - CONTENT - STATUS_CODE - DELTA]"
            f"[{resp.url}] - [{resp.content}] - [{resp.status_code}] "
            f"- [{resp.elapsed.total_seconds()}]"
        )
        if resp.status_code == 200:
            user.has_password_set_on_idms = True
            user.save()

    def create_idms_code(self):
        url = f"{settings.IDMS_BASE_URL}v1/o/authorize/"
        payload = {
            "client_id": settings.IDMS_CLIENT_ID,
            "redirect_uri": settings.IDMS_REDIRECT_URL,
            "scope": ["openid"],
            "response_type": "code",
        }
        resp = requests.post(url, json=payload)
        return resp.json().get("code")

    def create_idms_access_token(self):
        code = self.create_idms_code()
        url = f"{settings.IDMS_BASE_URL}v1/o/token/"
        payload = {
            "client_id": settings.IDMS_CLIENT_ID,
            "client_secret": settings.IDMS_CLIENT_SECRET,
            "redirect_uri": settings.IDMS_REDIRECT_URL,
            "grant_type": "authorization_code",
            "code": code,
            "sso_uid": settings.IDMS_SSO_UID,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        resp = requests.post(url, data=payload, headers=headers)
        return resp.json().get("access_token")

    def sso_login(self, username, password):
        url = f"{settings.IDMS_BASE_URL}accounts/login/"
        SSO_INTEGRATION_LOGGER.debug(
            f"SSO INTEGRATION LOGIN username: {username} password: {password}"
        )
        payload = {
            "login": username,
            "password": password,
        }
        resp = requests.post(url, json=payload)
        SSO_INTEGRATION_LOGGER.debug(
            f"SSO INTEGRATION LOGIN REQUEST [URL - CONTENT - STATUS_CODE - DELTA]"
            f"[{resp.url}] - [{resp.content}] - [{resp.status_code}] "
            f"- [{resp.elapsed.total_seconds()}]"
        )
        return resp.status_code == 200

    def authenticate(self, username, password):
        SSO_INTEGRATION_LOGGER.debug(
            f"SSO INTEGRATION AUTHENTICATE username: {username} password {password}"
        )
        try:
            user = User.objects.get(username=username)
            SSO_INTEGRATION_LOGGER.debug(
                f"SSO INTEGRATION AUTHENTICATE found user: {user} user_idms_id: {user.idms_user_id}"
                f" user has set password on IDMS {user.has_password_set_on_idms}"
            )
            if user.idms_user_id:
                if user.has_password_set_on_idms:
                    return user if self.sso_login(username, password) else None
                else:
                    if user.check_password(password):
                        self.change_user_password(user, password)
                        return user
                    return None
            else:
                return None
        except User.DoesNotExist:
            SSO_INTEGRATION_LOGGER.debug(
                f"SSO INTEGRATION AUTHENTICATE Exception user not found with username {username}"
            )
            return None
