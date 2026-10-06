from __future__ import annotations

from dataclasses import dataclass

from app.harban.enums import ServiceStatus


@dataclass(frozen=True)
class HarbanService:
    key: str
    name: str
    description: str
    status: ServiceStatus
    client_need_keywords: tuple[str, ...]


HARBAN_SERVICES: tuple[HarbanService, ...] = (
    HarbanService(
        key="llm_evaluation",
        name="AI / LLM evaluation & benchmarking",
        description=(
            "Authoring evaluation rubrics, verifier logic, and gold-reference solutions for code, "
            "reasoning, and safety tasks against frontier LLMs."
        ),
        status=ServiceStatus.DISCUSSION,
        client_need_keywords=("llm evaluation", "model evaluation", "benchmark", "eval harness", "model benchmark", "red team"),
    ),
    HarbanService(
        key="rag_knowledge",
        name="RAG & knowledge systems",
        description=(
            "Retrieval-augmented generation pipelines over proprietary knowledge bases: ingestion, "
            "chunking, embedding, hybrid search, and evaluated response generation."
        ),
        status=ServiceStatus.DISCUSSION,
        client_need_keywords=("rag", "retrieval augmented", "knowledge base", "vector search", "semantic search", "chatbot over docs"),
    ),
    HarbanService(
        key="ai_agent_engineering",
        name="AI agent engineering",
        description=(
            "Multi-step agent systems with tool use, planning, memory, and evaluation. "
            "Design, build, and test agentic workflows for well-scoped business tasks."
        ),
        status=ServiceStatus.DISCUSSION,
        client_need_keywords=("ai agent", "agentic", "langchain", "langgraph", "tool-use", "autogpt", "multi-step reasoning"),
    ),
    HarbanService(
        key="prototype_poc",
        name="Prototypes / POCs",
        description=(
            "Rapid, scoped prototypes of AI/LLM applications so clients can validate feasibility "
            "before committing to production investment."
        ),
        status=ServiceStatus.DISCUSSION,
        client_need_keywords=("prototype", "poc", "proof of concept", "mvp", "feasibility", "demo"),
    ),
    HarbanService(
        key="ai_automation",
        name="AI automation / data workflows",
        description=(
            "Pipelines that use LLMs to extract, classify, enrich, and act on data at scale — "
            "with evaluation gates and human-in-the-loop checkpoints."
        ),
        status=ServiceStatus.DISCUSSION,
        client_need_keywords=("ai automation", "llm pipeline", "data extraction", "data enrichment", "document ai", "workflow automation"),
    ),
    HarbanService(
        key="llm_training_support",
        name="LLM fine-tuning & training-data support",
        description=(
            "SFT / LoRA fine-tuning, RLHF data design, dataset curation, and training-run instrumentation "
            "for teams building their own models."
        ),
        status=ServiceStatus.DISCUSSION,
        client_need_keywords=("fine-tuning", "sft", "lora", "rlhf", "training data", "model training"),
    ),
    HarbanService(
        key="ai_advisory",
        name="AI research / advisory",
        description=(
            "Short-engagement advisory on model choice, evaluation strategy, cost/latency tradeoffs, "
            "and AI product scoping."
        ),
        status=ServiceStatus.DISCUSSION,
        client_need_keywords=("ai advisory", "ai consultant", "ai strategy", "model selection", "ai audit"),
    ),
)


def match_services(client_need_text: str) -> list[HarbanService]:
    text = (client_need_text or "").lower()
    hits: list[HarbanService] = []
    for svc in HARBAN_SERVICES:
        for kw in svc.client_need_keywords:
            if kw in text:
                hits.append(svc)
                break
    return hits


def truthful_service_label(svc: HarbanService) -> str:
    if svc.status == ServiceStatus.DELIVERED:
        return svc.name
    return f"{svc.name} (status: {svc.status.value} — not yet commercially delivered)"
