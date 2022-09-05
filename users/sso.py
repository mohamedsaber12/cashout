from django.conf import settings
import requests


class SSOIntegration:
    def register_user_on_idms(self, user):
        payload = {
            "username": user.username,
            "email": user.email,
        }
        url = f"{settings.IDMS_BASE_URL}accounts/signup/"
        resp = requests.post(url, json=payload)
        user.idms_user_id = resp.json().get("id")
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
