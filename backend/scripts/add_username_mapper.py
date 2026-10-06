"""Add a preferred_username protocol mapper to the minova-portal client (live realm).

Run:  python scripts/add_username_mapper.py
"""
import json
import urllib.parse
import urllib.request

KC = "http://localhost:8081"
REALM = "minova"
CLIENT_ID = "minova-portal"


def _post(url, payload, token=None, form=False):
    data = urllib.parse.urlencode(payload).encode() if form else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded" if form else "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as r:
        return r.status, r.read().decode()


def _get(url, token):
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def main():
    _, body = _post(
        f"{KC}/realms/master/protocol/openid-connect/token",
        {"grant_type": "password", "client_id": "admin-cli", "username": "admin", "password": "admin"},
        form=True,
    )
    admin_token = json.loads(body)["access_token"]

    clients = _get(f"{KC}/admin/realms/{REALM}/clients?clientId={CLIENT_ID}", admin_token)
    if not clients:
        raise SystemExit(f"client {CLIENT_ID} not found")
    client_uuid = clients[0]["id"]

    existing = _get(f"{KC}/admin/realms/{REALM}/clients/{client_uuid}/protocol-mappers/models", admin_token)
    if any(m["name"] == "username-mapper" for m in existing):
        print("username-mapper already present; nothing to do")
        return

    mapper = {
        "name": "username-mapper",
        "protocol": "openid-connect",
        "protocolMapper": "oidc-usermodel-property-mapper",
        "config": {
            "user.attribute": "username",
            "claim.name": "preferred_username",
            "jsonType.label": "String",
            "id.token.claim": "true",
            "access.token.claim": "true",
            "userinfo.token.claim": "true",
        },
    }
    status, _ = _post(
        f"{KC}/admin/realms/{REALM}/clients/{client_uuid}/protocol-mappers/models",
        mapper,
        token=admin_token,
    )
    print(f"mapper added: HTTP {status}")


if __name__ == "__main__":
    main()
