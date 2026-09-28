def test_list_providers(client):
    resp = client.get("/providers")
    assert resp.status_code == 200
    by_country = {p["country_code"]: p["provider"] for p in resp.json()}

    # Checks membership, not the whole set: the registry is meant to grow, so
    # pinning an exact set would break this test every time a country is added.
    assert by_country["AR"] == "AFIP"
    assert by_country["BR"] == "NFe"
