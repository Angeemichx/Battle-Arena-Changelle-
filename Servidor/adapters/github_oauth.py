import json
import urllib.parse
import urllib.request


class GithubOAuth:
    def __init__(self, client_id: str):
        self.client_id = client_id

    def _req(self, url, datos=None, token=None):
        headers = {"Accept": "application/json", "User-Agent": "battle-arena"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        body = urllib.parse.urlencode(datos).encode() if datos is not None else None
        req = urllib.request.Request(url, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.load(r)

    def iniciar(self) -> dict:
        return self._req("https://github.com/login/device/code",
                         {"client_id": self.client_id, "scope": "read:user user:email"})

    def consultar(self, device_code: str) -> dict:
        return self._req("https://github.com/login/oauth/access_token", {
            "client_id": self.client_id,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        })

    def perfil(self, token: str) -> dict:
        user = self._req("https://api.github.com/user", token=token)
        email = None
        for e in self._req("https://api.github.com/user/emails", token=token):
            if e.get("primary") and e.get("verified"):
                email = e["email"]
        return {"id": str(user["id"]), "login": user["login"], "email": email}