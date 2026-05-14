import json


def test_chat_returns_answer_sources_and_saves_session_history(integration):
    integration.seed_document(
        filename="contract.txt",
        text="Contract termination requires thirty days notice before cancellation.",
    )
    session_response = integration.client.post(
        "/api/v1/sessions",
        json={"metadata": {"test": True}},
    )
    assert session_response.status_code == 201
    session_id = session_response.json()["session_id"]

    response = integration.client.post(
        "/api/v1/chat",
        json={"query": "What does termination require?", "session_id": session_id, "top_k": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "termination requires thirty days notice" in payload["answer"]
    assert payload["sources"]
    assert payload["citation_validation"]["status"] in {"supported", "partially_supported"}
    assert payload["session_id"] == session_id
    assert integration.message_count(session_id) == 2


def test_streaming_chat_emits_sources_tokens_validation_and_done(integration):
    integration.seed_document(
        filename="contract.txt",
        text="Contract termination requires thirty days notice before cancellation.",
    )
    session_id = integration.client.post("/api/v1/sessions", json={}).json()["session_id"]

    with integration.client.stream(
        "POST",
        "/api/v1/chat",
        json={
            "query": "What does termination require?",
            "session_id": session_id,
            "top_k": 2,
            "stream": True,
        },
    ) as response:
        assert response.status_code == 200
        events = [
            json.loads(line.removeprefix("data: "))
            for line in response.iter_lines()
            if line.startswith("data: ")
        ]

    assert [event["type"] for event in events] == [
        "sources",
        "token",
        "token",
        "token",
        "citation_validation",
        "done",
    ]
    assert integration.message_count(session_id) == 2


def test_chat_without_ready_documents_returns_400(integration):
    response = integration.client.post("/api/v1/chat", json={"query": "Anything indexed?"})

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "no_documents"
