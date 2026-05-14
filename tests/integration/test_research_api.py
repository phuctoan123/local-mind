def test_research_returns_steps_sources_and_validation(integration):
    integration.seed_document(
        filename="contract.txt",
        text=(
            "Contract termination requires thirty days notice. "
            "The policy also notes risk review before cancellation."
        ),
    )

    response = integration.client.post(
        "/api/v1/research",
        json={"query": "What are the termination risks?", "max_steps": 3, "top_k_per_step": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "termination requires thirty days notice" in payload["answer"]
    assert payload["steps"]
    assert payload["sources"]
    assert payload["citation_validation"]["status"] in {"supported", "partially_supported"}
    assert payload["latency_ms"] >= 0


def test_research_without_ready_documents_returns_400(integration):
    response = integration.client.post(
        "/api/v1/research",
        json={"query": "What are the termination risks?"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "no_documents"
