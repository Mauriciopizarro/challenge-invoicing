from tests.conftest import corrupt_extra_fields, register_merchant, register_recipient


def test_mx_recipient_missing_codigo_postal_marks_invoice_failed(client):
    # Registration already blocks this, so simulate drift after a valid one.
    merchant_id = register_merchant(client, "MX")
    recipient_id = register_recipient(client, "MX")
    corrupt_extra_fields("recipients", recipient_id)

    resp = client.post(
        "/invoices",
        json={
            "entity_id": "e1",
            "amount": 10.0,
            "issuer_merchant_id": merchant_id,
            "recipient_id": recipient_id,
        },
        headers={"Idempotency-Key": "mx-missing-cp-1"},
    )
    invoice_id = resp.json()["invoice_id"]

    detail = client.get(f"/invoices/{invoice_id}").json()
    assert detail["status"] == "failed"
    assert "codigo_postal" in detail["failure_reason"]


def test_correcting_a_merchant_does_not_change_already_issued_invoices(client):
    merchant_id = register_merchant(client, "AR", legal_name="Acme Argentna SA")
    recipient_id = register_recipient(client, "AR")

    resp = client.post(
        "/invoices",
        json={
            "entity_id": "e1",
            "amount": 10.0,
            "issuer_merchant_id": merchant_id,
            "recipient_id": recipient_id,
        },
        headers={"Idempotency-Key": "pre-correction-1"},
    )
    invoice_id = resp.json()["invoice_id"]
    before = client.get(f"/invoices/{invoice_id}").json()
    assert before["issuer"]["legal_name"] == "Acme Argentna SA"

    put_resp = client.put(
        f"/merchants/{merchant_id}",
        json={
            "legal_name": "Acme Argentina SA",
            "tax_id": {"id_type": "CUIT", "value": "30-12345678-9"},
            "address": "Av. Corrientes 1234, CABA",
            "extra": {"condicion_iva": "Responsable Inscripto"},
        },
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["fiscal_party"]["legal_name"] == "Acme Argentina SA"

    after = client.get(f"/invoices/{invoice_id}").json()
    assert after["issuer"]["legal_name"] == "Acme Argentna SA"  # unchanged, still the old (wrong) snapshot

    # A NEW invoice from the same (now-corrected) merchant picks up the fix.
    resp2 = client.post(
        "/invoices",
        json={
            "entity_id": "e1",
            "amount": 20.0,
            "issuer_merchant_id": merchant_id,
            "recipient_id": recipient_id,
        },
        headers={"Idempotency-Key": "post-correction-1"},
    )
    new_invoice = client.get(f"/invoices/{resp2.json()['invoice_id']}").json()
    assert new_invoice["issuer"]["legal_name"] == "Acme Argentina SA"


def test_correcting_a_recipient_does_not_change_already_issued_invoices(client):
    """Mirror of the merchant version above, for the recipient side."""
    merchant_id = register_merchant(client, "AR")
    recipient_id = register_recipient(client, "AR", legal_name="Cliente SRLL")

    resp = client.post(
        "/invoices",
        json={
            "entity_id": "e1",
            "amount": 10.0,
            "issuer_merchant_id": merchant_id,
            "recipient_id": recipient_id,
        },
        headers={"Idempotency-Key": "pre-recipient-correction-1"},
    )
    invoice_id = resp.json()["invoice_id"]
    before = client.get(f"/invoices/{invoice_id}").json()
    assert before["recipient"]["legal_name"] == "Cliente SRLL"

    put_resp = client.put(
        f"/recipients/{recipient_id}",
        json={
            "legal_name": "Cliente SRL",
            "tax_id": {"id_type": "CUIT", "value": "20-98765432-1"},
            "address": "San Martin 500, Rosario",
            "extra": {"condicion_iva": "Responsable Inscripto"},
        },
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["fiscal_party"]["legal_name"] == "Cliente SRL"

    after = client.get(f"/invoices/{invoice_id}").json()
    assert after["recipient"]["legal_name"] == "Cliente SRLL"  # unchanged, still the old snapshot

    resp2 = client.post(
        "/invoices",
        json={
            "entity_id": "e1",
            "amount": 20.0,
            "issuer_merchant_id": merchant_id,
            "recipient_id": recipient_id,
        },
        headers={"Idempotency-Key": "post-recipient-correction-1"},
    )
    new_invoice = client.get(f"/invoices/{resp2.json()['invoice_id']}").json()
    assert new_invoice["recipient"]["legal_name"] == "Cliente SRL"


def test_issuer_with_drifted_incomplete_fiscal_data_marks_invoice_failed(client):
    # Registration already blocks this (test_merchant_registration_rejects_
    # missing_required_fiscal_field); this proves the second line of defense,
    # send_invoice's own revalidation, by simulating drift directly at the DB.
    merchant_id = register_merchant(client, "AR")
    recipient_id = register_recipient(client, "AR")
    corrupt_extra_fields("merchants", merchant_id)

    resp = client.post(
        "/invoices",
        json={
            "entity_id": "e1",
            "amount": 10.0,
            "issuer_merchant_id": merchant_id,
            "recipient_id": recipient_id,
        },
        headers={"Idempotency-Key": "issuer-drift-1"},
    )
    invoice_id = resp.json()["invoice_id"]

    detail = client.get(f"/invoices/{invoice_id}").json()
    assert detail["status"] == "failed"
    assert "issuer" in detail["failure_reason"]
    assert "condicion_iva" in detail["failure_reason"]
