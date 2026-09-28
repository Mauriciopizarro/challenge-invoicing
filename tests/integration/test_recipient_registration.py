from tests.fakes.fiscal_data import fiscal_party_payload


def test_register_recipient_happy_path(client):
    resp = client.post(
        "/recipients",
        json={"country_code": "AR", "fiscal_party": fiscal_party_payload("AR")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["country_code"] == "AR"
    assert body["fiscal_party"]["tax_id"]["id_type"] == "CUIT"

    detail = client.get(f"/recipients/{body['recipient_id']}")
    assert detail.status_code == 200
    assert detail.json() == body


def test_unsupported_country_rejected(client):
    resp = client.post(
        "/recipients",
        json={"country_code": "CL", "fiscal_party": fiscal_party_payload("AR")},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "unsupported_country"


def test_recipient_registration_rejects_missing_required_fiscal_field(client):
    resp = client.post(
        "/recipients",
        json={"country_code": "AR", "fiscal_party": fiscal_party_payload("AR", extra={})},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "invalid_fiscal_data"
    assert "condicion_iva" in body["error"]["message"]


def test_recipient_registration_rejects_missing_recipient_only_field(client):
    # codigo_postal is recipient-only (CFDI 4.0 "Domicilio Fiscal Receptor"),
    # so this must be rejected even though a Merchant with the same data passes.
    resp = client.post(
        "/recipients",
        json={"country_code": "MX", "fiscal_party": fiscal_party_payload("MX", extra={"regimen_fiscal": "601"})},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "invalid_fiscal_data"
    assert "codigo_postal" in body["error"]["message"]


def test_recipient_registration_rejects_wrong_tax_id_type(client):
    resp = client.post(
        "/recipients",
        json={"country_code": "AR", "fiscal_party": fiscal_party_payload("MX")},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "invalid_fiscal_data"
    assert "tax id type" in body["error"]["message"]


def test_get_unknown_recipient_returns_404(client):
    resp = client.get("/recipients/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "recipient_not_found"


def test_update_recipient_corrects_fiscal_data(client):
    created = client.post(
        "/recipients",
        json={"country_code": "AR", "fiscal_party": fiscal_party_payload("AR", legal_name="Cliente SRLL")},
    ).json()
    recipient_id = created["recipient_id"]

    corrected = fiscal_party_payload("AR", legal_name="Cliente SRL")
    resp = client.put(f"/recipients/{recipient_id}", json=corrected)
    assert resp.status_code == 200
    body = resp.json()
    assert body["fiscal_party"]["legal_name"] == "Cliente SRL"
    assert body["country_code"] == "AR"  # unchanged
    assert body["updated_at"] != body["created_at"]

    fetched = client.get(f"/recipients/{recipient_id}").json()
    assert fetched["fiscal_party"]["legal_name"] == "Cliente SRL"


def test_update_recipient_rejects_missing_required_fiscal_field(client):
    recipient_id = client.post(
        "/recipients", json={"country_code": "AR", "fiscal_party": fiscal_party_payload("AR")}
    ).json()["recipient_id"]

    resp = client.put(f"/recipients/{recipient_id}", json=fiscal_party_payload("AR", extra={}))
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_fiscal_data"


def test_update_recipient_rejects_wrong_tax_id_type(client):
    recipient_id = client.post(
        "/recipients", json={"country_code": "AR", "fiscal_party": fiscal_party_payload("AR")}
    ).json()["recipient_id"]

    resp = client.put(f"/recipients/{recipient_id}", json=fiscal_party_payload("MX"))
    assert resp.status_code == 422
    assert "tax id type" in resp.json()["error"]["message"]


def test_update_unknown_recipient_returns_404(client):
    resp = client.put(
        "/recipients/00000000-0000-0000-0000-000000000000",
        json=fiscal_party_payload("AR"),
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "recipient_not_found"
