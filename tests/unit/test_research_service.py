import asyncio

from app.models.research import ResearchRequest
from app.services.research_service import (
    ResearchService,
    build_research_prompt,
    plan_research_queries,
)
from app.services.vector_store import RetrievedChunk


def test_plan_research_queries_splits_comparison_question():
    queries = plan_research_queries("Compare pricing and termination terms", max_steps=4)

    assert queries[0] == "Compare pricing and termination terms"
    assert "Compare pricing" in queries
    assert "termination terms" in queries


def test_build_research_prompt_includes_steps_and_sources():
    prompt = build_research_prompt(
        "Compare policies",
        [("pricing", [_chunk(0, "Pricing is monthly.", 1)])],
    )

    assert "Step 1: pricing" in prompt
    assert "agreement.pdf" in prompt
    assert "Pricing is monthly." in prompt


def test_research_service_runs_steps_and_validates_answer(monkeypatch):
    monkeypatch.setattr(
        "app.services.research_service.settings",
        FakeSettings(),
    )
    service = ResearchService(FakeRetrievalEngine(), FakeLLMClient())

    response = asyncio.run(
        service.research(
            ResearchRequest(
                query="Compare pricing and termination",
                max_steps=3,
                top_k_per_step=2,
            )
        )
    )

    assert response.steps
    assert response.sources
    assert "agreement.pdf" in response.answer
    assert response.citation_validation is not None


class FakeSettings:
    min_similarity_score = 0.15
    max_context_tokens = 1200
    llm_temperature = 0.1
    llm_top_p = 0.9
    llm_num_ctx = 2048
    llm_num_predict = 256
    enable_citation_validation = True


class FakeRetrievalEngine:
    async def retrieve(self, query: str, **_kwargs) -> list[RetrievedChunk]:
        return [_chunk(abs(hash(query)) % 1000, "Pricing is monthly. Termination needs notice.", 1)]


class FakeLLMClient:
    async def generate(self, *_args, **_kwargs) -> str:
        return "Pricing is monthly and termination needs notice (agreement.pdf page 1)."


def _chunk(index: int, text: str, page_number: int) -> RetrievedChunk:
    return RetrievedChunk(
        document_id="doc-1",
        filename="agreement.pdf",
        page_number=page_number,
        chunk_index=index,
        text=text,
        score=0.9,
        char_start=0,
        char_end=len(text),
    )
