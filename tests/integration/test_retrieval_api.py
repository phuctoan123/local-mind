def test_retrieve_chunks_returns_ranked_sources(integration):
    contract = integration.seed_document(
        filename="contract.txt",
        text="Contract termination requires thirty days notice before cancellation.",
    )
    integration.seed_document(
        filename="invoice.txt",
        text="Invoice payment is due within seven days after receipt.",
    )

    response = integration.client.post(
        "/api/v1/chunks",
        json={"query": "termination notice", "top_k": 3, "min_score": 0.0},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "list"
    assert payload["data"]
    assert payload["data"][0]["document_id"] == contract["id"]
    assert "termination" in payload["data"][0]["text"].lower()


def test_retrieve_chunks_respects_document_filter(integration):
    integration.seed_document(
        filename="contract.txt",
        text="Contract termination requires thirty days notice before cancellation.",
    )
    invoice = integration.seed_document(
        filename="invoice.txt",
        text="Invoice payment is due within seven days after receipt.",
    )

    response = integration.client.post(
        "/api/v1/chunks",
        json={
            "query": "payment",
            "document_ids": [invoice["id"]],
            "top_k": 3,
            "min_score": 0.0,
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data
    assert {item["document_id"] for item in data} == {invoice["id"]}


def test_retrieval_debug_exposes_pipeline_stages(integration):
    integration.seed_document(
        filename="contract.txt",
        text="Contract termination requires thirty days notice before cancellation.",
    )

    response = integration.client.post(
        "/api/v1/chunks/debug",
        json={"query": "termination notice", "top_k": 2, "min_score": 0.0},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "retrieval_debug"
    assert payload["mode"] == "hybrid"
    assert payload["vector"]
    assert payload["bm25"]
    assert payload["fused"]
    assert payload["reranked"]
    assert payload["data"]
