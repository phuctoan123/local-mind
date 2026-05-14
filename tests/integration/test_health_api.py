def test_health_reports_sqlite_migrations_and_fake_providers(integration):
    response = integration.client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["components"]["sqlite"]["status"] == "ok"
    assert payload["components"]["sqlite"]["details"]["migrations"]["pending"] == []
    assert payload["components"]["vector_store"]["details"]["backend"] == "sqlite-vector"
    assert payload["components"]["llm"]["details"]["chat"]["model"] == "fake-llm"
    assert payload["components"]["llm"]["details"]["embedding"]["model"] == "fake-embedding"
