from __future__ import annotations

from app.schemas.company import Company


PRIORITY_COMPANIES: list[dict] = [
    {"name": "OpenAI", "canonical": "openai", "categories": ["foundation-model", "ai"], "priority_score": 100, "careers_url": "https://openai.com/careers"},
    {"name": "Anthropic", "canonical": "anthropic", "categories": ["foundation-model", "ai"], "priority_score": 100, "careers_url": "https://www.anthropic.com/jobs"},
    {"name": "Google DeepMind", "canonical": "google-deepmind", "categories": ["foundation-model", "research"], "priority_score": 100, "careers_url": "https://deepmind.google/careers/"},
    {"name": "Google", "canonical": "google", "categories": ["big-tech", "ai"], "priority_score": 95, "careers_url": "https://careers.google.com/"},
    {"name": "Microsoft", "canonical": "microsoft", "categories": ["big-tech", "ai"], "priority_score": 95, "careers_url": "https://careers.microsoft.com/"},
    {"name": "Meta", "canonical": "meta", "categories": ["big-tech", "ai"], "priority_score": 95, "careers_url": "https://www.metacareers.com/"},
    {"name": "NVIDIA", "canonical": "nvidia", "categories": ["ai-hardware", "ai"], "priority_score": 95, "careers_url": "https://www.nvidia.com/en-us/about-nvidia/careers/"},
    {"name": "Amazon", "canonical": "amazon", "categories": ["big-tech"], "priority_score": 90, "careers_url": "https://www.amazon.jobs/"},
    {"name": "AWS", "canonical": "aws", "categories": ["cloud", "ai"], "priority_score": 90, "careers_url": "https://aws.amazon.com/careers/"},
    {"name": "Apple", "canonical": "apple", "categories": ["big-tech"], "priority_score": 90, "careers_url": "https://www.apple.com/careers/"},
    {"name": "xAI", "canonical": "xai", "categories": ["foundation-model"], "priority_score": 95, "careers_url": "https://x.ai/careers"},
    {"name": "Mistral AI", "canonical": "mistral-ai", "categories": ["foundation-model"], "priority_score": 95, "careers_url": "https://mistral.ai/careers/"},
    {"name": "Cohere", "canonical": "cohere", "categories": ["foundation-model"], "priority_score": 90, "careers_url": "https://cohere.com/careers"},
    {"name": "Perplexity", "canonical": "perplexity", "categories": ["ai-product"], "priority_score": 90, "careers_url": "https://www.perplexity.ai/hub/careers"},
    {"name": "Hugging Face", "canonical": "huggingface", "categories": ["open-source", "ai"], "priority_score": 95, "careers_url": "https://apply.workable.com/huggingface/"},
    {"name": "Scale AI", "canonical": "scale-ai", "categories": ["ai-data"], "priority_score": 95, "careers_url": "https://scale.com/careers"},
    {"name": "Databricks", "canonical": "databricks", "categories": ["data-platform", "ml"], "priority_score": 90, "careers_url": "https://www.databricks.com/company/careers"},
    {"name": "Snowflake", "canonical": "snowflake", "categories": ["data-platform"], "priority_score": 85, "careers_url": "https://careers.snowflake.com/"},
    {"name": "Cursor (Anysphere)", "canonical": "anysphere", "categories": ["dev-tools", "ai"], "priority_score": 95, "careers_url": "https://cursor.com/careers"},
    {"name": "Replit", "canonical": "replit", "categories": ["dev-tools"], "priority_score": 90, "careers_url": "https://replit.com/careers"},
    {"name": "Together AI", "canonical": "together-ai", "categories": ["llm-infra"], "priority_score": 90, "careers_url": "https://www.together.ai/careers"},
    {"name": "Groq", "canonical": "groq", "categories": ["ai-hardware"], "priority_score": 90, "careers_url": "https://groq.com/careers/"},
    {"name": "ElevenLabs", "canonical": "elevenlabs", "categories": ["ai-product"], "priority_score": 85, "careers_url": "https://elevenlabs.io/careers"},
    {"name": "LangChain", "canonical": "langchain", "categories": ["dev-tools", "ai"], "priority_score": 85, "careers_url": "https://www.langchain.com/careers"},
    {"name": "Weights & Biases", "canonical": "weights-and-biases", "categories": ["mlops"], "priority_score": 85, "careers_url": "https://wandb.ai/site/careers"},
    {"name": "OpenRouter", "canonical": "openrouter", "categories": ["llm-infra"], "priority_score": 80, "careers_url": "https://openrouter.ai/careers"},
    {"name": "Fireworks AI", "canonical": "fireworks-ai", "categories": ["llm-infra"], "priority_score": 85, "careers_url": "https://fireworks.ai/careers"},
    {"name": "Replicate", "canonical": "replicate", "categories": ["llm-infra"], "priority_score": 80, "careers_url": "https://replicate.com/careers"},
    {"name": "Handshake AI", "canonical": "handshake-ai", "categories": ["ai-data", "evaluation"], "priority_score": 90, "careers_url": "https://joinhandshake.ai/"},
    {"name": "Surge AI", "canonical": "surge-ai", "categories": ["ai-data"], "priority_score": 85, "careers_url": "https://www.surgehq.ai/careers"},
    {"name": "Outlier", "canonical": "outlier", "categories": ["ai-data"], "priority_score": 75, "careers_url": "https://outlier.ai/"},
    {"name": "TELUS Digital AI", "canonical": "telus-digital-ai", "categories": ["ai-data"], "priority_score": 70, "careers_url": "https://www.telusinternational.com/careers"},
]


def build_company_rows() -> list[Company]:
    out: list[Company] = []
    for c in PRIORITY_COMPANIES:
        out.append(
            Company(
                name=c["name"],
                canonical_name=c["canonical"],
                careers_url=c.get("careers_url"),
                categories=c.get("categories", []),
                is_priority=True,
                priority_score=c.get("priority_score", 50),
            )
        )
    return out
