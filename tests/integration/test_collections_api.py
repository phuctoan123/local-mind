def test_collection_document_workflow(integration):
    ready_doc = integration.seed_document(
        filename="contract.txt",
        text="Contract termination requires thirty days notice.",
        status="READY",
    )
    pending_doc = integration.seed_document(
        filename="draft.txt",
        text="Draft policy waiting for ingestion.",
        status="PENDING",
    )

    create_response = integration.client.post("/api/v1/collections", json={"name": "Contracts"})
    assert create_response.status_code == 201
    collection = create_response.json()

    duplicate_response = integration.client.post("/api/v1/collections", json={"name": "Contracts"})
    assert duplicate_response.status_code == 409

    add_ready = integration.client.put(
        f"/api/v1/collections/{collection['id']}/documents/{ready_doc['id']}"
    )
    add_pending = integration.client.put(
        f"/api/v1/collections/{collection['id']}/documents/{pending_doc['id']}"
    )
    assert add_ready.status_code == 200
    assert add_ready.json()["assigned"] is True
    assert add_pending.status_code == 200

    list_response = integration.client.get("/api/v1/collections")
    assert list_response.status_code == 200
    assert list_response.json()["collections"][0]["document_count"] == 2

    docs_response = integration.client.get("/api/v1/documents")
    assert docs_response.status_code == 200
    documents = {document["id"]: document for document in docs_response.json()["documents"]}
    assert collection["id"] in documents[ready_doc["id"]]["collection_ids"]
    assert collection["id"] in documents[pending_doc["id"]]["collection_ids"]

    ready_response = integration.client.get(
        f"/api/v1/collections/{collection['id']}/ready-documents"
    )
    assert ready_response.status_code == 200
    assert ready_response.json()["document_ids"] == [ready_doc["id"]]

    remove_response = integration.client.delete(
        f"/api/v1/collections/{collection['id']}/documents/{pending_doc['id']}"
    )
    assert remove_response.status_code == 200
    assert remove_response.json()["assigned"] is False

    delete_response = integration.client.delete(f"/api/v1/collections/{collection['id']}")
    assert delete_response.status_code == 204
    assert integration.client.get("/api/v1/collections").json()["collections"] == []


def test_adding_missing_document_to_collection_returns_404(integration):
    collection = integration.client.post("/api/v1/collections", json={"name": "Contracts"}).json()

    response = integration.client.put(
        f"/api/v1/collections/{collection['id']}/documents/missing-document"
    )

    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "not_found"
