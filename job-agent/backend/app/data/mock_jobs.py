from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.schemas import Job, JobCreate
from app.schemas.enums import (
    ApplicationMethod,
    EmploymentType,
    JobSource,
    RemotePolicy,
    ShiftType,
)
from app.schemas.job import SalaryRange


def _ago(hours: int = 0, days: int = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=hours, days=days)


def _mock() -> list[JobCreate]:
    jobs: list[JobCreate] = []

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-ai-ant-001",
        company="Anthropic", company_url="https://www.anthropic.com",
        title="AI Engineer, Applied Research",
        location="Remote - Global",
        remote=RemotePolicy.REMOTE_GLOBAL_UNVERIFIED,
        employment_type=EmploymentType.FULL_TIME,
        shift=ShiftType.FLEXIBLE,
        salary=SalaryRange(min_value=250000, max_value=400000, currency="USD", unit="year"),
        description=(
            "Join Anthropic's Applied Research team to build and deploy LLM-powered applications. "
            "You will fine-tune (SFT, RLHF) foundation models, design evaluations, and operate production "
            "inference pipelines. Collaborate across research, safety, and product. Strong Python, PyTorch, "
            "distributed training, and prompt-engineering skills required."
        ),
        requirements=["Python", "PyTorch", "LLM", "RLHF", "SFT", "evaluation", "docker"],
        preferred_skills=["RAG", "distributed training", "Kubernetes"],
        responsibilities=["Fine-tune Claude variants", "Build evaluations", "Deploy inference pipelines"],
        application_url="https://www.anthropic.com/jobs/ai-engineer-applied-research",
        application_method=ApplicationMethod.COMPANY_SITE,
        posted_at=_ago(hours=4),
    ))

    jobs.append(JobCreate(
        source=JobSource.COMPANY_CAREERS, source_job_id="openai-llm-001",
        company="OpenAI", company_url="https://openai.com",
        title="LLM Engineer, Evaluations",
        location="Remote - US",
        remote=RemotePolicy.REMOTE_COUNTRY,
        employment_type=EmploymentType.FULL_TIME,
        shift=ShiftType.FLEXIBLE,
        salary=SalaryRange(min_value=300000, max_value=550000, currency="USD", unit="year"),
        description=(
            "Design and ship evaluations for frontier LLMs. Author rubrics, build verifier logic, "
            "manage datasets at scale, and own benchmark pipelines for code, reasoning, and safety. "
            "Experience with pytest-style verifiers and gold-reference solutions highly valued."
        ),
        requirements=["Python", "LLM", "evaluation", "rubric design", "pytest"],
        preferred_skills=["RLHF", "SFT", "verifier design", "docker"],
        application_url="https://openai.com/careers/llm-engineer-evaluations",
        application_method=ApplicationMethod.COMPANY_SITE,
        posted_at=_ago(hours=10),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-ggl-ai-002",
        company="Google",
        title="Software Engineer, AI",
        location="Gurugram, India (Hybrid)",
        remote=RemotePolicy.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        shift=ShiftType.DAY,
        salary=SalaryRange(min_value=3500000, max_value=6500000, currency="INR", unit="year"),
        description=(
            "Build large-scale AI systems that serve billions. Work on LLM infrastructure, retrieval, "
            "ranking, and inference. You will own backend services, work with Python and Java, and "
            "collaborate with research. 2+ years of software engineering experience required."
        ),
        requirements=["Python", "Java", "LLM", "distributed systems", "2 years experience"],
        preferred_skills=["PyTorch", "TensorFlow", "RAG"],
        application_url="https://www.linkedin.com/jobs/view/li-ggl-ai-002",
        application_method=ApplicationMethod.PLATFORM_APPLY,
        posted_at=_ago(hours=20),
    ))

    jobs.append(JobCreate(
        source=JobSource.NAUKRI, source_job_id="naukri-ggl-ai-002-dup",
        company="Google India",
        title="AI Software Engineer",
        location="Gurgaon, Haryana",
        remote=RemotePolicy.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=3500000, max_value=6500000, currency="INR", unit="year", raw="₹35L - ₹65L / year"),
        description="Build large-scale AI systems. Python/Java. 2+ years. Based in Gurgaon.",
        requirements=["Python", "Java", "LLM", "2 years experience"],
        application_url="https://www.naukri.com/job-listings-naukri-ggl-ai-002-dup",
        application_method=ApplicationMethod.PLATFORM_APPLY,
        posted_at=_ago(hours=18),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-ms-003",
        company="Microsoft", company_url="https://careers.microsoft.com",
        title="Applied Scientist, Generative AI",
        location="Noida, India (Hybrid)",
        remote=RemotePolicy.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        shift=ShiftType.DAY,
        salary=SalaryRange(min_value=2500000, max_value=4500000, currency="INR", unit="year"),
        description=(
            "Join the Microsoft India AI team to build generative AI products. Research and ship LLM "
            "features for Copilot. Strong Python, PyTorch, and research experience. 3+ years."
        ),
        requirements=["Python", "PyTorch", "LLM", "generative AI", "3 years experience"],
        preferred_skills=["RAG", "RLHF", "prompt engineering"],
        application_url="https://careers.microsoft.com/jobs/li-ms-003",
        application_method=ApplicationMethod.COMPANY_SITE,
        posted_at=_ago(hours=36),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-nvda-004",
        company="NVIDIA",
        title="Senior ML Platform Engineer",
        location="Bangalore, India",
        remote=RemotePolicy.ONSITE,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=4500000, max_value=7000000, currency="INR", unit="year"),
        description="Design and maintain internal ML platform. 8+ years of production ML experience. Senior role.",
        requirements=["Python", "Kubernetes", "PyTorch", "8 years experience"],
        application_url="https://www.linkedin.com/jobs/view/li-nvda-004",
        posted_at=_ago(days=2),
    ))

    jobs.append(JobCreate(
        source=JobSource.WELLFOUND, source_job_id="wf-perplexity-005",
        company="Perplexity",
        title="Applied AI Engineer",
        location="Remote - India / Global",
        remote=RemotePolicy.REMOTE_GLOBAL_UNVERIFIED,
        employment_type=EmploymentType.FULL_TIME,
        shift=ShiftType.FLEXIBLE,
        salary=SalaryRange(min_value=200000, max_value=350000, currency="USD", unit="year"),
        description=(
            "Build and ship the next generation of search. You'll work on retrieval, ranking, and LLM "
            "orchestration. Python, PyTorch, RAG expertise required. Comfort with async, async-first team."
        ),
        requirements=["Python", "RAG", "LLM", "retrieval"],
        preferred_skills=["PyTorch", "ranking"],
        application_url="https://wellfound.com/perplexity/jobs/005",
        posted_at=_ago(hours=8),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-hf-006",
        company="Hugging Face",
        title="LLM Engineer - Evaluations (Remote)",
        location="Remote - Global",
        remote=RemotePolicy.REMOTE_GLOBAL_UNVERIFIED,
        employment_type=EmploymentType.FULL_TIME,
        shift=ShiftType.ASYNC,
        salary=SalaryRange(min_value=140000, max_value=220000, currency="USD", unit="year"),
        description=(
            "Own LLM evaluation harnesses. Design benchmarks, author verifier logic, and ship reproducible "
            "pipelines. Experience with pytest, Docker, and model evaluation preferred."
        ),
        requirements=["Python", "LLM", "evaluation", "pytest"],
        preferred_skills=["RLHF", "Docker", "transformers"],
        application_url="https://apply.workable.com/huggingface/li-hf-006",
        posted_at=_ago(hours=12),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-scale-007",
        company="Scale AI",
        title="AI Evaluation Engineer (Part-time, Remote)",
        location="Remote - India (contract)",
        remote=RemotePolicy.REMOTE_COUNTRY,
        employment_type=EmploymentType.PART_TIME,
        shift=ShiftType.FLEXIBLE,
        hours_per_week=20,
        salary=SalaryRange(min_value=40, max_value=65, currency="USD", unit="hour"),
        description=(
            "Design and author tasks for evaluating frontier LLMs on code and reasoning. Part-time, 20h/week, "
            "flexible timezone. Experience with RLHF, SFT, benchmark design, pytest preferred."
        ),
        requirements=["Python", "LLM", "evaluation", "benchmark design"],
        preferred_skills=["RLHF", "SFT", "pytest", "docker"],
        application_url="https://scale.com/careers/li-scale-007",
        posted_at=_ago(hours=5),
    ))

    jobs.append(JobCreate(
        source=JobSource.OUTLIER, source_job_id="outlier-rlhf-008",
        company="Outlier",
        title="AI Trainer - Code (Freelance, Remote)",
        location="Remote - Global",
        remote=RemotePolicy.REMOTE_GLOBAL,
        employment_type=EmploymentType.FREELANCE,
        shift=ShiftType.ASYNC,
        hours_per_week=15,
        salary=SalaryRange(min_value=25, max_value=40, currency="USD", unit="hour"),
        description=(
            "Contribute code-focused tasks and RLHF annotations for frontier LLM training. Set your own hours, "
            "async-first, project-based. Strong Python, Java or C++ required."
        ),
        requirements=["Python", "code review"],
        preferred_skills=["Java", "C++", "RLHF"],
        application_url="https://outlier.ai/apply/008",
        posted_at=_ago(hours=6),
    ))

    jobs.append(JobCreate(
        source=JobSource.HANDSHAKE_AI, source_job_id="hs-ai-dynamo-009",
        company="Handshake AI",
        title="AI Fellow - Project Dynamo (Contract)",
        location="Remote - Global",
        remote=RemotePolicy.REMOTE_GLOBAL,
        employment_type=EmploymentType.CONTRACT,
        shift=ShiftType.ASYNC,
        hours_per_week=20,
        salary=SalaryRange(min_value=50, max_value=80, currency="USD", unit="hour"),
        description=(
            "Author ML infrastructure benchmark tasks: PyTorch training tasks, evaluation datasets, gold "
            "reference solutions, and verifier logic (gradient-norm trace checks) for code and reasoning "
            "model assessment. Contract engagement."
        ),
        requirements=["Python", "PyTorch", "benchmark design", "verifier design"],
        preferred_skills=["RLHF", "SFT", "gold solutions"],
        application_url="https://joinhandshake.ai/apply/hs-ai-dynamo-009",
        posted_at=_ago(hours=3),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-cursor-010",
        company="Cursor",
        title="AI Coding Agent Engineer",
        location="Remote - Global",
        remote=RemotePolicy.REMOTE_GLOBAL_UNVERIFIED,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=250000, max_value=500000, currency="USD", unit="year"),
        description=(
            "Build the agent that powers Cursor's AI pair programmer. Design orchestration, tools, and "
            "evaluations. Strong Python + TypeScript. Experience with LLM agents and codegen."
        ),
        requirements=["Python", "TypeScript", "LLM", "agents"],
        preferred_skills=["evaluation", "tool-use", "codegen"],
        application_url="https://cursor.com/careers/li-cursor-010",
        posted_at=_ago(hours=14),
    ))

    jobs.append(JobCreate(
        source=JobSource.NAUKRI, source_job_id="naukri-011",
        company="Fractal Analytics",
        title="Generative AI Engineer",
        location="Gurugram, Haryana (Hybrid)",
        remote=RemotePolicy.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        shift=ShiftType.DAY,
        salary=SalaryRange(min_value=1800000, max_value=3200000, currency="INR", unit="year", raw="₹18-32 LPA"),
        description="Build GenAI products for Fortune 500 clients. Python, LangChain, RAG, prompt engineering. 2+ years.",
        requirements=["Python", "LangChain", "RAG", "prompt engineering", "2 years experience"],
        preferred_skills=["Azure OpenAI", "GCP"],
        application_url="https://www.naukri.com/job/011",
        posted_at=_ago(hours=22),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-ivs-012",
        company="InfoVision",
        title="AI/ML Engineer - LLM Fine-tuning",
        location="Noida, Sector 62",
        remote=RemotePolicy.ONSITE,
        employment_type=EmploymentType.FULL_TIME,
        shift=ShiftType.DAY,
        salary=SalaryRange(min_value=1200000, max_value=2200000, currency="INR", unit="year"),
        description="Fine-tune (SFT/LoRA) LLMs on client datasets. PyTorch, HuggingFace. 1-3 years experience.",
        requirements=["Python", "PyTorch", "LLM", "SFT", "LoRA", "1 years experience"],
        preferred_skills=["HuggingFace", "RLHF"],
        application_url="https://www.linkedin.com/jobs/view/li-ivs-012",
        posted_at=_ago(hours=18),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-swiggy-013",
        company="Swiggy",
        title="Senior Software Engineer - Backend",
        location="Gurugram, India",
        remote=RemotePolicy.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=2500000, max_value=4500000, currency="INR", unit="year"),
        description="Build backend services at Swiggy. Python, Java, Go. 5+ years of production backend experience.",
        requirements=["Python", "Java", "backend", "5 years experience"],
        application_url="https://www.linkedin.com/jobs/view/li-swiggy-013",
        posted_at=_ago(hours=30),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-razorpay-014",
        company="Razorpay",
        title="Backend Engineer (Python)",
        location="Bangalore / Remote India",
        remote=RemotePolicy.REMOTE_COUNTRY,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=1800000, max_value=3500000, currency="INR", unit="year"),
        description="Build payments infrastructure. Python, Postgres, Redis, Kafka. 2-5 years.",
        requirements=["Python", "SQL", "backend", "2 years experience"],
        preferred_skills=["Kafka", "Redis"],
        application_url="https://www.linkedin.com/jobs/view/li-razorpay-014",
        posted_at=_ago(hours=44),
    ))

    jobs.append(JobCreate(
        source=JobSource.REMOTEOK, source_job_id="ro-015",
        company="Replicate",
        title="ML Engineer (Remote, Contract)",
        location="Remote - Global",
        remote=RemotePolicy.REMOTE_GLOBAL,
        employment_type=EmploymentType.CONTRACT,
        shift=ShiftType.ASYNC,
        hours_per_week=25,
        salary=SalaryRange(min_value=70, max_value=120, currency="USD", unit="hour"),
        description="Build model-hosting infrastructure. Python, PyTorch, Docker, Kubernetes. Async team.",
        requirements=["Python", "PyTorch", "Docker"],
        preferred_skills=["Kubernetes", "model serving"],
        application_url="https://remoteok.com/l/ro-015",
        posted_at=_ago(hours=16),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-weremote-016",
        company="Weights & Biases",
        title="MLOps Engineer (Remote)",
        location="Remote - APAC",
        remote=RemotePolicy.REMOTE_COUNTRY,
        employment_type=EmploymentType.FULL_TIME,
        shift=ShiftType.FLEXIBLE,
        salary=SalaryRange(min_value=150000, max_value=230000, currency="USD", unit="year"),
        description="Build and run the W&B platform. Python, Go, Kubernetes, distributed systems.",
        requirements=["Python", "Kubernetes", "distributed systems"],
        preferred_skills=["Go", "monitoring"],
        application_url="https://wandb.ai/site/careers/li-weremote-016",
        posted_at=_ago(hours=28),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-elev-017",
        company="ElevenLabs",
        title="Research Engineer - Audio / Diffusion",
        location="Remote - Global",
        remote=RemotePolicy.REMOTE_GLOBAL_UNVERIFIED,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=180000, max_value=320000, currency="USD", unit="year"),
        description="Research and ship audio generation models. PyTorch, diffusion models, HuggingFace.",
        requirements=["Python", "PyTorch", "diffusion models"],
        preferred_skills=["HuggingFace", "audio"],
        application_url="https://elevenlabs.io/careers/li-elev-017",
        posted_at=_ago(hours=40),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-lc-018",
        company="LangChain",
        title="Developer Advocate - AI Agents (Remote)",
        location="Remote - Global",
        remote=RemotePolicy.REMOTE_GLOBAL_UNVERIFIED,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=140000, max_value=200000, currency="USD", unit="year"),
        description="Build sample agents, author docs, present at conferences. Python, LangChain, LLMs.",
        requirements=["Python", "LangChain", "LLM", "agents"],
        preferred_skills=["public speaking", "technical writing"],
        application_url="https://www.langchain.com/careers/li-lc-018",
        posted_at=_ago(hours=48),
    ))

    jobs.append(JobCreate(
        source=JobSource.NAUKRI, source_job_id="naukri-paypal-019",
        company="PayPal",
        title="Software Engineer II",
        location="Chennai, India",
        remote=RemotePolicy.ONSITE,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=1800000, max_value=2800000, currency="INR", unit="year"),
        description="Build backend services at PayPal. Java, Python. 2+ years.",
        requirements=["Java", "Python", "backend", "2 years experience"],
        application_url="https://www.naukri.com/job/naukri-paypal-019",
        posted_at=_ago(days=1),
    ))

    jobs.append(JobCreate(
        source=JobSource.NAUKRI, source_job_id="naukri-walmart-020",
        company="Walmart Global Tech",
        title="Data Engineer - Python",
        location="Gurgaon, Cyber City",
        remote=RemotePolicy.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        shift=ShiftType.DAY,
        salary=SalaryRange(min_value=1500000, max_value=2600000, currency="INR", unit="year"),
        description="Build data pipelines on GCP + BigQuery. Python, SQL, Airflow. 2-4 years.",
        requirements=["Python", "SQL", "data engineering", "2 years experience"],
        preferred_skills=["GCP", "Airflow"],
        application_url="https://www.naukri.com/job/naukri-walmart-020",
        posted_at=_ago(hours=50),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-walmart-020-dup",
        company="Walmart Global Tech India",
        title="Data Engineer, Python",
        location="Gurugram, Haryana",
        remote=RemotePolicy.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=1500000, max_value=2600000, currency="INR", unit="year"),
        description="Build data pipelines on GCP + BigQuery. Python, SQL, Airflow. 2-4 years.",
        requirements=["Python", "SQL", "data engineering"],
        application_url="https://www.linkedin.com/jobs/view/li-walmart-020-dup",
        posted_at=_ago(hours=52),
    ))

    jobs.append(JobCreate(
        source=JobSource.WELLFOUND, source_job_id="wf-sarvam-021",
        company="Sarvam AI",
        title="LLM Research Engineer (Bangalore / Remote)",
        location="Bangalore / Remote India",
        remote=RemotePolicy.REMOTE_COUNTRY,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=2000000, max_value=4500000, currency="INR", unit="year"),
        description="Build India-focused foundation models. Pretraining, SFT, RLHF, evaluation. PyTorch.",
        requirements=["Python", "PyTorch", "SFT", "RLHF", "LLM"],
        preferred_skills=["pretraining", "evaluation"],
        application_url="https://wellfound.com/sarvam/jobs/021",
        posted_at=_ago(hours=6),
    ))

    jobs.append(JobCreate(
        source=JobSource.WELLFOUND, source_job_id="wf-krutrim-022",
        company="Krutrim",
        title="Senior AI Engineer - RAG",
        location="Bangalore (Hybrid)",
        remote=RemotePolicy.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=2500000, max_value=4500000, currency="INR", unit="year"),
        description="Build RAG applications. Python, LangChain, vector DBs. 4+ years.",
        requirements=["Python", "RAG", "LangChain", "4 years experience"],
        preferred_skills=["vector databases"],
        application_url="https://wellfound.com/krutrim/jobs/022",
        posted_at=_ago(hours=14),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-zepto-023",
        company="Zepto",
        title="Python Developer - Growth",
        location="Delhi NCR (Hybrid)",
        remote=RemotePolicy.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=1500000, max_value=2800000, currency="INR", unit="year"),
        description="Build growth analytics backend. Python, SQL, FastAPI. 1-3 years.",
        requirements=["Python", "SQL", "FastAPI", "1 years experience"],
        application_url="https://www.linkedin.com/jobs/view/li-zepto-023",
        posted_at=_ago(days=1),
    ))

    jobs.append(JobCreate(
        source=JobSource.INSTAHYRE, source_job_id="ih-024",
        company="Observe AI",
        title="Full Stack Engineer - Python/React",
        location="Bangalore / Remote India",
        remote=RemotePolicy.REMOTE_COUNTRY,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=1800000, max_value=3500000, currency="INR", unit="year"),
        description="Build voice-AI product UI. Python backend, React frontend. 2+ years.",
        requirements=["Python", "React", "JavaScript", "2 years experience"],
        preferred_skills=["FastAPI", "TypeScript"],
        application_url="https://www.instahyre.com/job/ih-024",
        posted_at=_ago(hours=20),
    ))

    jobs.append(JobCreate(
        source=JobSource.WEWORKREMOTELY, source_job_id="wwr-025",
        company="Buildkite",
        title="Backend Engineer (Remote)",
        location="Remote - APAC",
        remote=RemotePolicy.REMOTE_COUNTRY,
        employment_type=EmploymentType.FULL_TIME,
        shift=ShiftType.ASYNC,
        salary=SalaryRange(min_value=120000, max_value=180000, currency="USD", unit="year"),
        description="Build CI/CD platform. Elixir, Ruby, Postgres. Open to Python engineers willing to learn.",
        requirements=["backend", "SQL"],
        preferred_skills=["Elixir", "Ruby", "Python"],
        application_url="https://weworkremotely.com/l/wwr-025",
        posted_at=_ago(days=2),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-dwavelet-026",
        company="DeepWavelet AI",
        title="AI Agent Engineer (Part-time, Remote India)",
        location="Remote - India",
        remote=RemotePolicy.REMOTE_COUNTRY,
        employment_type=EmploymentType.PART_TIME,
        shift=ShiftType.EVENING,
        hours_per_week=20,
        salary=SalaryRange(min_value=1800, max_value=3000, currency="INR", unit="hour", raw="₹1800-3000/hr"),
        description=(
            "Build agentic AI pipelines for enterprise clients. Python, LangChain or LangGraph, tool-use, "
            "evaluations. 20 hours/week, flexible evening schedule."
        ),
        requirements=["Python", "LangChain", "agents", "LLM"],
        preferred_skills=["LangGraph", "evaluation"],
        application_url="https://www.linkedin.com/jobs/view/li-dwavelet-026",
        posted_at=_ago(hours=4),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-crossover-027",
        company="Crossover",
        title="Chief AI Officer - Fortune 500 Client",
        location="Remote - Global",
        remote=RemotePolicy.REMOTE_GLOBAL,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=400000, max_value=800000, currency="USD", unit="year"),
        description="Chief AI Officer role requiring 15+ years of ML leadership. Executive position.",
        requirements=["ML leadership", "15 years experience"],
        application_url="https://www.linkedin.com/jobs/view/li-crossover-027",
        posted_at=_ago(days=3),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-ms-vp-028",
        company="Meta",
        title="VP of Engineering - Generative AI",
        location="Menlo Park, CA",
        remote=RemotePolicy.ONSITE,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=600000, max_value=1200000, currency="USD", unit="year"),
        description="VP role. 20+ years of engineering leadership. H-1B sponsorship not available.",
        requirements=["engineering leadership", "20 years experience"],
        application_url="https://www.linkedin.com/jobs/view/li-ms-vp-028",
        posted_at=_ago(days=4),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-029",
        company="XYZ Fintech",
        title="Nurse - Night Shift (Delhi)",
        location="Delhi",
        remote=RemotePolicy.ONSITE,
        employment_type=EmploymentType.FULL_TIME,
        shift=ShiftType.NIGHT,
        salary=SalaryRange(min_value=30000, max_value=50000, currency="INR", unit="month", raw="₹30-50k/month"),
        description="Hiring experienced nurse for night shift at Delhi hospital. BSc Nursing required.",
        requirements=["BSc Nursing", "nursing experience"],
        application_url="https://www.linkedin.com/jobs/view/li-029",
        posted_at=_ago(days=1),
    ))

    jobs.append(JobCreate(
        source=JobSource.NAUKRI, source_job_id="naukri-030",
        company="MegaBiz Marketing",
        title="Field Sales Executive - FMCG",
        location="Gurgaon, Haryana",
        remote=RemotePolicy.ONSITE,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=20000, max_value=40000, currency="INR", unit="month"),
        description="Door-to-door FMCG sales. Multi-level marketing opportunity. Earn unlimited income.",
        requirements=["sales", "2-wheeler"],
        application_url="https://www.naukri.com/job/naukri-030",
        posted_at=_ago(days=2),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-scam-031",
        company="Private Employer",
        title="Data Entry Work From Home - Earn ₹2 Lakh Per Day",
        location="Remote - Global",
        remote=RemotePolicy.REMOTE_GLOBAL_UNVERIFIED,
        employment_type=EmploymentType.PART_TIME,
        salary=SalaryRange(raw="₹2 lakh per day guaranteed"),
        description=(
            "Easy data entry job. Earn ₹2 lakh per day. Registration fee of ₹5000 required to start. "
            "Contact only on WhatsApp +91-99999-99999. Payment through PayPal friends and family or Bitcoin wallet. "
            "No experience required. Unlimited earning potential!"
        ),
        requirements=["basic typing"],
        application_url="https://suspicious-site.tk/apply",
        application_method=ApplicationMethod.FORM_URL,
        application_email="hr@gmail.com",
        posted_at=_ago(hours=2),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-scam-032",
        company="GlobalCrypto Investments",
        title="Crypto Trading Assistant",
        location="Remote",
        remote=RemotePolicy.REMOTE_GLOBAL_UNVERIFIED,
        employment_type=EmploymentType.PART_TIME,
        description=(
            "Trade crypto on our platform. Send USDT security deposit upfront to activate your account. "
            "Payment in Bitcoin. Telegram only: @cryptoboss2024."
        ),
        requirements=[],
        application_url="https://trade-bot.gq",
        application_email="support@yahoo.com",
        posted_at=_ago(hours=1),
    ))

    jobs.append(JobCreate(
        source=JobSource.NAUKRI, source_job_id="naukri-scam-033",
        company="Confidential Company",
        title="Form Filling Work From Home",
        location="Remote - India",
        remote=RemotePolicy.REMOTE_COUNTRY,
        employment_type=EmploymentType.PART_TIME,
        description=(
            "Simple form filling work. Pay training fee of ₹2000 to receive your login kit. "
            "Multi-level marketing opportunity with downline bonuses."
        ),
        requirements=["none"],
        application_url="https://quick-earn.xyz/apply",
        posted_at=_ago(days=1),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-fw-034",
        company="Fireworks AI",
        title="LLM Infrastructure Engineer",
        location="Remote - Global",
        remote=RemotePolicy.REMOTE_GLOBAL_UNVERIFIED,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=200000, max_value=350000, currency="USD", unit="year"),
        description=(
            "Build inference infrastructure for open-source LLMs. CUDA, Triton, PyTorch, Python, Go. "
            "3+ years of production infra experience."
        ),
        requirements=["Python", "PyTorch", "CUDA", "3 years experience"],
        preferred_skills=["Triton", "Go"],
        application_url="https://fireworks.ai/careers/li-fw-034",
        posted_at=_ago(hours=28),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-groq-035",
        company="Groq",
        title="ML Compiler Engineer (Remote)",
        location="Remote - Global",
        remote=RemotePolicy.REMOTE_GLOBAL_UNVERIFIED,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=220000, max_value=400000, currency="USD", unit="year"),
        description="Build ML compilers for Groq's LPU. C++, MLIR, Python. 5+ years.",
        requirements=["C++", "MLIR", "Python", "5 years experience"],
        application_url="https://groq.com/careers/li-groq-035",
        posted_at=_ago(days=2),
    ))

    jobs.append(JobCreate(
        source=JobSource.WELLFOUND, source_job_id="wf-ola-036",
        company="OlaKrutrim Labs",
        title="Applied AI Engineer, Multilingual LLM",
        location="Noida (Hybrid)",
        remote=RemotePolicy.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=2000000, max_value=4000000, currency="INR", unit="year"),
        description=(
            "Build multilingual (Hindi, Maithili, Tamil, Bengali) LLM pipelines. Python, PyTorch, "
            "evaluation frameworks. 2+ years."
        ),
        requirements=["Python", "PyTorch", "multilingual", "LLM", "2 years experience"],
        preferred_skills=["Hindi NLP", "evaluation"],
        application_url="https://wellfound.com/ola/jobs/wf-ola-036",
        posted_at=_ago(hours=10),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-pepp-037",
        company="Peppo",
        title="Python Backend Developer (Night Shift)",
        location="Gurugram, India",
        remote=RemotePolicy.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        shift=ShiftType.NIGHT,
        salary=SalaryRange(min_value=1500000, max_value=2500000, currency="INR", unit="year"),
        description=(
            "Night-shift backend engineering role (8pm-5am IST) for a US-serving fintech. Python, FastAPI, Postgres. 2+ years."
        ),
        requirements=["Python", "FastAPI", "SQL", "2 years experience"],
        application_url="https://www.linkedin.com/jobs/view/li-pepp-037",
        posted_at=_ago(hours=16),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-abt-038",
        company="Abstract AI",
        title="AI Evaluation Contractor (Remote India, Evening)",
        location="Remote - India",
        remote=RemotePolicy.REMOTE_COUNTRY,
        employment_type=EmploymentType.CONTRACT,
        shift=ShiftType.EVENING,
        hours_per_week=15,
        salary=SalaryRange(min_value=1200, max_value=2000, currency="INR", unit="hour", raw="₹1200-2000/hr"),
        description=(
            "Author SFT and RLHF evaluation tasks for code and reasoning models. 15 hours/week, 6PM-9PM IST, async-friendly. "
            "Python + pytest + prior LLM evaluation experience."
        ),
        requirements=["Python", "pytest", "LLM", "evaluation"],
        preferred_skills=["SFT", "RLHF"],
        application_url="https://www.linkedin.com/jobs/view/li-abt-038",
        posted_at=_ago(hours=3),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-cognizant-039",
        company="Cognizant",
        title="Senior Software Engineer - Full Stack (Night Shift)",
        location="Noida, Sector 125",
        remote=RemotePolicy.ONSITE,
        employment_type=EmploymentType.FULL_TIME,
        shift=ShiftType.NIGHT,
        salary=SalaryRange(min_value=1500000, max_value=2200000, currency="INR", unit="year"),
        description="US-shift role (10pm-7am IST). React + Node.js. 5+ years.",
        requirements=["React", "Node.js", "JavaScript", "5 years experience"],
        application_url="https://www.linkedin.com/jobs/view/li-cognizant-039",
        posted_at=_ago(days=2),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-mindtickle-040",
        company="MindTickle",
        title="AI Software Engineer - LLM Products",
        location="Gurugram (Hybrid)",
        remote=RemotePolicy.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=2000000, max_value=3500000, currency="INR", unit="year"),
        description="Build LLM-powered sales-enablement features. Python, OpenAI API, RAG, vector DBs. 2+ years.",
        requirements=["Python", "LLM", "RAG", "2 years experience"],
        preferred_skills=["OpenAI API", "vector DBs"],
        application_url="https://www.linkedin.com/jobs/view/li-mindtickle-040",
        posted_at=_ago(hours=24),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-stripe-041",
        company="Stripe",
        title="Software Engineer - Python",
        location="Bangalore / Remote India",
        remote=RemotePolicy.REMOTE_COUNTRY,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=3500000, max_value=6000000, currency="INR", unit="year"),
        description="Build payments infra. Python, Ruby, distributed systems. 3+ years.",
        requirements=["Python", "distributed systems", "3 years experience"],
        preferred_skills=["Ruby"],
        application_url="https://www.linkedin.com/jobs/view/li-stripe-041",
        posted_at=_ago(days=1),
    ))

    jobs.append(JobCreate(
        source=JobSource.NAUKRI, source_job_id="naukri-dam-042",
        company="DataAnnotation.tech",
        title="AI Trainer - Code & Reasoning (Freelance)",
        location="Remote - Global",
        remote=RemotePolicy.REMOTE_GLOBAL,
        employment_type=EmploymentType.FREELANCE,
        shift=ShiftType.ASYNC,
        hours_per_week=20,
        salary=SalaryRange(min_value=20, max_value=40, currency="USD", unit="hour"),
        description="Train frontier LLMs via SFT and RLHF annotations. Code + math + reasoning projects.",
        requirements=["Python", "code review"],
        preferred_skills=["RLHF", "SFT"],
        application_url="https://www.naukri.com/job/naukri-dam-042",
        posted_at=_ago(hours=10),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-redhat-043",
        company="Red Hat",
        title="Senior AI Platform Engineer",
        location="Pune, India",
        remote=RemotePolicy.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=3000000, max_value=5000000, currency="INR", unit="year"),
        description="Build OpenShift AI platform. Python, Go, Kubernetes. 7+ years.",
        requirements=["Python", "Kubernetes", "7 years experience"],
        application_url="https://www.linkedin.com/jobs/view/li-redhat-043",
        posted_at=_ago(days=3),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-nokia-044",
        company="Nokia",
        title="Software Engineer Intern (Summer)",
        location="Bangalore, India",
        remote=RemotePolicy.ONSITE,
        employment_type=EmploymentType.INTERNSHIP,
        salary=SalaryRange(raw="₹40,000/month stipend"),
        description="Summer internship for pre-final-year students.",
        requirements=["currently pursuing B.Tech"],
        application_url="https://www.linkedin.com/jobs/view/li-nokia-044",
        posted_at=_ago(days=5),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-nebius-045",
        company="Nebius AI",
        title="AI Infrastructure Engineer (Remote India/Europe)",
        location="Remote - Europe / India",
        remote=RemotePolicy.REMOTE_COUNTRY,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=90000, max_value=160000, currency="USD", unit="year"),
        description="Build GPU cloud infrastructure. Python, Kubernetes, CUDA. 3+ years.",
        requirements=["Python", "Kubernetes", "3 years experience"],
        preferred_skills=["CUDA"],
        application_url="https://www.linkedin.com/jobs/view/li-nebius-045",
        posted_at=_ago(hours=18),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-glean-046",
        company="Glean",
        title="Search/Retrieval ML Engineer",
        location="Bangalore (Hybrid)",
        remote=RemotePolicy.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=3000000, max_value=5500000, currency="INR", unit="year"),
        description="Build enterprise search + RAG. Python, PyTorch, embedding models. 3+ years.",
        requirements=["Python", "PyTorch", "RAG", "retrieval", "3 years experience"],
        application_url="https://www.linkedin.com/jobs/view/li-glean-046",
        posted_at=_ago(hours=22),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-notion-047",
        company="Notion",
        title="Software Engineer - AI Features",
        location="Remote - Global",
        remote=RemotePolicy.REMOTE_GLOBAL_UNVERIFIED,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=180000, max_value=280000, currency="USD", unit="year"),
        description="Build Notion AI features. Python, TypeScript, OpenAI/Anthropic APIs. 3+ years.",
        requirements=["Python", "TypeScript", "LLM", "3 years experience"],
        application_url="https://www.linkedin.com/jobs/view/li-notion-047",
        posted_at=_ago(days=1),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-anth-contract-048",
        company="Anthropic",
        title="Contract: LLM Safety Evaluation Author (Part-time, Remote)",
        location="Remote - Global",
        remote=RemotePolicy.REMOTE_GLOBAL,
        employment_type=EmploymentType.CONTRACT,
        shift=ShiftType.ASYNC,
        hours_per_week=15,
        salary=SalaryRange(min_value=60, max_value=100, currency="USD", unit="hour"),
        description=(
            "Author safety-focused evaluations for Claude. Design red-team prompts, evaluation rubrics, "
            "and verifier scripts. 15 hours/week, 3-6 month engagement."
        ),
        requirements=["Python", "LLM", "evaluation", "safety"],
        preferred_skills=["rubric design", "pytest"],
        application_url="https://www.anthropic.com/jobs/li-anth-contract-048",
        posted_at=_ago(hours=2),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-adobe-049",
        company="Adobe",
        title="AI/ML Engineer - Firefly",
        location="Noida, India (Hybrid)",
        remote=RemotePolicy.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        salary=SalaryRange(min_value=2500000, max_value=4500000, currency="INR", unit="year"),
        description="Build generative image/video models. Python, PyTorch, diffusion. 3+ years.",
        requirements=["Python", "PyTorch", "diffusion models", "3 years experience"],
        application_url="https://www.linkedin.com/jobs/view/li-adobe-049",
        posted_at=_ago(hours=30),
    ))

    jobs.append(JobCreate(
        source=JobSource.LINKEDIN, source_job_id="li-rev-050",
        company="Revelio Labs",
        title="Python Developer - Data Platform (Remote, Weekends OK)",
        location="Remote - Global",
        remote=RemotePolicy.REMOTE_GLOBAL_UNVERIFIED,
        employment_type=EmploymentType.CONTRACT,
        shift=ShiftType.WEEKEND,
        hours_per_week=10,
        salary=SalaryRange(min_value=30, max_value=55, currency="USD", unit="hour"),
        description="Weekend contractor to help ship data platform features. Python, SQL, FastAPI. Async.",
        requirements=["Python", "SQL", "FastAPI"],
        application_url="https://www.linkedin.com/jobs/view/li-rev-050",
        posted_at=_ago(hours=4),
    ))

    jobs.append(JobCreate(
        source=JobSource.COMPANY_CAREERS, source_job_id="indie-ai-051",
        company="IndieAI Labs",
        title="AI Engineer (Contract, Remote India)",
        location="Remote - India",
        remote=RemotePolicy.REMOTE_COUNTRY,
        employment_type=EmploymentType.CONTRACT,
        shift=ShiftType.FLEXIBLE,
        hours_per_week=20,
        salary=SalaryRange(min_value=35, max_value=55, currency="USD", unit="hour"),
        description=(
            "Small AI consulting firm hiring a contract AI engineer. Python, PyTorch, LLM fine-tuning, "
            "RAG. Email applications to hiring@indieailabs.co with your resume."
        ),
        requirements=["Python", "PyTorch", "LLM", "RAG"],
        application_url="https://indieailabs.co/jobs/ai-engineer",
        application_method=ApplicationMethod.EMAIL,
        application_email="hiring@indieailabs.co",
        posted_at=_ago(hours=5),
    ))

    return jobs


def build_mock_jobs() -> list[Job]:
    out: list[Job] = []
    for jc in _mock():
        out.append(Job.from_create(jc))
    return out
