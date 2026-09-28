from tests.fakes.fiscal_data import fiscal_party_payload


def test_register_merchant_happy_path(client):
    resp = client.post(
        "/merchants",
        json={"country_code": "AR", "fiscal_party": fiscal_party_payload("AR")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["country_code"] == "AR"
    assert body["fiscal_party"]["tax_id"]["id_type"] == "CUIT"

    detail = client.get(f"/merchants/{body['merchant_id']}")
    assert detail.status_code == 200
    assert detail.json() == body


def test_unsupported_country_rejected(client):
    resp = client.post(
        "/merchants",
        json={"country_code": "CL", "fiscal_party": fiscal_party_payload("AR")},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "unsupported_country"


def test_merchant_registration_rejects_missing_required_fiscal_field(client):
    resp = client.post(
        "/merchants",
        json={"country_code": "AR", "fiscal_party": fiscal_party_payload("AR", extra={})},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "invalid_fiscal_data"
    assert "condicion_iva" in body["error"]["message"]


def test_merchant_registration_rejects_wrong_tax_id_type(client):
    # MX's tax id is an RFC, not a CUIT — registering an AR merchant with it
    # must be rejected up front, not only discovered later at invoice time.
    resp = client.post(
        "/merchants",
        json={"country_code": "AR", "fiscal_party": fiscal_party_payload("MX")},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "invalid_fiscal_data"
    assert "tax id type" in body["error"]["message"]


def test_get_unknown_merchant_returns_404(client):
    resp = client.get("/merchants/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "merchant_not_found"


def test_update_merchant_corrects_fiscal_data(client):
    created = client.post(
        "/merchants",
        json={"country_code": "AR", "fiscal_party": fiscal_party_payload("AR", legal_name="Acme Argentna SA")},
    ).json()
    merchant_id = created["merchant_id"]

    corrected = fiscal_party_payload("AR", legal_name="Acme Argentina SA")
    resp = client.put(f"/merchants/{merchant_id}", json=corrected)
    assert resp.status_code == 200
    body = resp.json()
    assert body["fiscal_party"]["legal_name"] == "Acme Argentina SA"
    assert body["country_code"] == "AR"  # unchanged
    assert body["updated_at"] != body["created_at"]

    fetched = client.get(f"/merchants/{merchant_id}").json()
    assert fetched["fiscal_party"]["legal_name"] == "Acme Argentina SA"


def test_update_merchant_rejects_missing_required_fiscal_field(client):
    merchant_id = client.post(
        "/merchants", json={"country_code": "AR", "fiscal_party": fiscal_party_payload("AR")}
    ).json()["merchant_id"]

    resp = client.put(f"/merchants/{merchant_id}", json=fiscal_party_payload("AR", extra={}))
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_fiscal_data"


def test_update_merchant_rejects_wrong_tax_id_type(client):
    merchant_id = client.post(
        "/merchants", json={"country_code": "AR", "fiscal_party": fiscal_party_payload("AR")}
    ).json()["merchant_id"]

    resp = client.put(f"/merchants/{merchant_id}", json=fiscal_party_payload("MX"))
    assert resp.status_code == 422
    assert "tax id type" in resp.json()["error"]["message"]


def test_update_unknown_merchant_returns_404(client):
    resp = client.put(
        "/merchants/00000000-0000-0000-0000-000000000000",
        json=fiscal_party_payload("AR"),
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "merchant_not_found"
