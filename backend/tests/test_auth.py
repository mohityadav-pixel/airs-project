def test_registration_returns_a_working_token(client):
    response = client.post("/api/v1/auth/register", json={
        "email": "new.user@example.com", "full_name": "New User",
        "password": "a-long-enough-password"})
    assert response.status_code == 201
    token = response.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "new.user@example.com"


def test_self_registration_cannot_claim_a_privileged_role(client):
    """A client that posts `role: admin` must still get a citizen account."""
    response = client.post("/api/v1/auth/register", json={
        "email": "sneaky@example.com", "full_name": "Sneaky",
        "password": "a-long-enough-password", "role": "admin"})
    assert response.status_code == 201
    token = response.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["role"] == "citizen"


def test_duplicate_email_is_rejected(client):
    payload = {"email": "dupe@example.com", "full_name": "Dupe",
               "password": "a-long-enough-password"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload).status_code == 400


def test_short_passwords_are_rejected(client):
    response = client.post("/api/v1/auth/register", json={
        "email": "short@example.com", "full_name": "Short", "password": "abc"})
    assert response.status_code == 422


def test_wrong_password_and_unknown_user_are_indistinguishable(client):
    unknown = client.post("/api/v1/auth/login", json={
        "email": "nobody@example.com", "password": "a-long-enough-password"})
    client.post("/api/v1/auth/register", json={
        "email": "known@example.com", "full_name": "Known",
        "password": "a-long-enough-password"})
    wrong = client.post("/api/v1/auth/login", json={
        "email": "known@example.com", "password": "definitely-wrong-pw"})
    assert unknown.status_code == wrong.status_code == 403
    assert unknown.json()["error"]["message"] == wrong.json()["error"]["message"]


def test_me_requires_a_token(client):
    assert client.get("/api/v1/auth/me").status_code == 403


def test_a_tampered_token_is_rejected(client, citizen_token):
    bad = citizen_token[:-4] + "aaaa"
    assert client.get("/api/v1/auth/me",
                      headers={"Authorization": f"Bearer {bad}"}).status_code == 403


def test_command_center_is_closed_to_citizens(client, citizen_token):
    response = client.get("/api/v1/command-center?city=delhi",
                          headers={"Authorization": f"Bearer {citizen_token}"})
    assert response.status_code == 403


def test_command_center_is_open_to_officials(client, official_token):
    response = client.get("/api/v1/command-center?city=delhi",
                          headers={"Authorization": f"Bearer {official_token}"})
    assert response.status_code == 200
    assert "zones" in response.json()


def test_admin_only_user_list_is_closed_to_officials(client, official_token):
    assert client.get("/api/v1/auth/users",
                      headers={"Authorization": f"Bearer {official_token}"}
                      ).status_code == 403
