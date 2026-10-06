from __future__ import annotations

from datetime import date
from pathlib import Path

from app.profile.schema import (
    Availability,
    Education,
    Experience,
    LocationPreferences,
    Profile,
    Project,
    ResumeVariant,
    SkillCategory,
    WorkAuthorization,
)


def build_default_profile(resume_root: Path | None = None) -> Profile:
    resume_root = resume_root or Path("resumes")

    experiences = [
        Experience(
            company="Ethara AI",
            role="Software Engineer",
            employment_type="Full-time",
            start_date=date(2025, 2, 1),
            end_date=None,
            location="Gurugram, India",
            is_remote=False,
            is_current=True,
            bullets=[
                "Train and fine-tune large language models (supervised fine-tuning and RLHF) across multiple projects, "
                "tracking loss curves, convergence, and evaluation metrics for stable, reproducible performance.",
                "Build containerized ML environments with Docker for reproducible training and inference; "
                "manage code, experiments, and reviews via Git/GitHub (feature branching, PRs, CI checks).",
                "Develop and integrate REST APIs to serve models and expose training/evaluation pipelines; "
                "engineer large-scale dataset preparation, cleaning, and validation for supervised learning workflows.",
            ],
            skills_used=[
                "Python", "PyTorch", "SFT", "LoRA", "RLHF", "Docker", "Git", "GitHub",
                "REST APIs", "CI/CD", "LLM training", "Evaluation metrics",
            ],
        ),
        Experience(
            company="Handshake AI (Project Dynamo)",
            role="AI Fellow / Benchmark Author",
            employment_type="Independent Contractor",
            start_date=date(2024, 1, 1),
            end_date=None,
            location="Remote",
            is_remote=True,
            is_current=True,
            bullets=[
                "Selected as AI Fellow; authored and verified ML infrastructure benchmark tasks — "
                "PyTorch training tasks, evaluation datasets, gold reference solutions, and verifier logic "
                "(including gradient-norm trace checks) for code and reasoning model assessment.",
            ],
            skills_used=["PyTorch", "Benchmark Design", "Gold Solutions", "Verifier Design", "LLM Evaluation"],
        ),
        Experience(
            company="Multi-SWE-bench",
            role="Multi-language SWE Task Author",
            employment_type="Independent Contractor",
            start_date=date(2024, 1, 1),
            end_date=None,
            location="Remote",
            is_remote=True,
            is_current=True,
            bullets=[
                "Authored and validated multi-language software-engineering tasks (Python, Java, JS): "
                "task instructions, oracle solutions, Dockerized repos, and pytest-based test/eval rubrics; "
                "performed human attempts (no LLMs) to calibrate pass/fail criteria.",
            ],
            skills_used=["Python", "Java", "JavaScript", "Docker", "pytest", "Task Design", "Evaluation Rubrics"],
        ),
        Experience(
            company="Harbor Benchmark",
            role="ML Benchmark Author",
            employment_type="Independent Contractor",
            start_date=date(2024, 1, 1),
            end_date=None,
            location="Remote",
            is_remote=True,
            is_current=True,
            bullets=[
                "Built end-to-end reproducible ML tasks (data prep, model training, evaluation) with "
                "gold reference solutions and automated, rubric-based grading of model outputs.",
            ],
            skills_used=["ML pipelines", "Reproducibility", "Grading rubrics", "Gold Solutions"],
        ),
        Experience(
            company="Turing",
            role="Code / STEM RLHF Contributor",
            employment_type="Independent Contractor",
            start_date=date(2024, 1, 1),
            end_date=None,
            location="Remote",
            is_remote=True,
            is_current=True,
            bullets=[
                "Delivered code and STEM RLHF, prompt engineering, and response evaluation for LLM training pipelines; "
                "designed advanced math problems with verified step-by-step solutions to probe model reasoning.",
            ],
            skills_used=["RLHF", "Prompt Engineering", "Response Evaluation", "STEM reasoning"],
        ),
        Experience(
            company="Outlier AI",
            role="LLM RLHF / Evaluation Contributor",
            employment_type="Independent Contractor",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 1, 1),
            location="Remote",
            is_remote=True,
            is_current=False,
            bullets=[
                "LLM RLHF, data annotation, model evaluation, and multilingual work (Hindi, English, Maithili).",
            ],
            skills_used=["RLHF", "Data Annotation", "Model Evaluation", "Multilingual"],
        ),
    ]

    projects = [
        Project(
            name="Resume–JD Matcher",
            date_range="2025",
            tech_stack=["Python", "Gemini API", "RAG-style Retrieval", "Streamlit", "pypdf"],
            bullets=[
                "Built and deployed a live LLM application that parses resumes (pypdf), retrieves and matches them "
                "against job descriptions, and generates structured fit analysis via the Gemini API; "
                "deployed on Streamlit Cloud with a production-usable UI.",
            ],
        ),
        Project(
            name="VideoGenAI",
            date_range="Feb 2025 – Jun 2025",
            tech_stack=["Python", "PyTorch", "Hugging Face Transformers", "Diffusion Models"],
            bullets=[
                "Built a controllable video-generation system creating short videos from images and text prompts "
                "using diffusion models; managed environment setup, inference workflows, and model configurations "
                "for production-scale outputs.",
            ],
        ),
        Project(
            name="Human Activity Recognition",
            date_range="Apr 2024 – Jun 2024",
            tech_stack=["Python", "Pandas", "NumPy", "Scikit-learn"],
            bullets=[
                "Developed an ML model classifying human activities from smartphone accelerometer/gyroscope data; "
                "applied data cleaning, feature engineering, and time-series evaluation to achieve high accuracy.",
            ],
        ),
    ]

    skill_categories = [
        SkillCategory(name="Languages", skills=["Python", "Java", "C", "SQL", "JavaScript", "Bash"]),
        SkillCategory(
            name="LLM & GenAI",
            skills=[
                "LLM Fine-tuning", "SFT", "LoRA", "RLHF", "RAG", "Retrieval-Augmented Generation",
                "Prompt Engineering", "Gemini API", "Hugging Face Transformers", "Diffusion Models",
                "LLM Training", "LLM Evaluation",
            ],
        ),
        SkillCategory(
            name="ML & DL",
            skills=["PyTorch", "Scikit-learn", "NumPy", "Pandas", "Matplotlib", "Statistics", "Probability"],
        ),
        SkillCategory(
            name="Benchmarking & Eval",
            skills=[
                "Task Design", "Oracle Solutions", "Gold Solutions", "Evaluation Rubrics",
                "Verifier Design", "pytest", "Model Evaluation", "Metrics", "Human Calibration",
                "AI Benchmarking", "RLHF", "SFT",
            ],
        ),
        SkillCategory(
            name="MLOps & Infra",
            skills=[
                "Docker", "Git", "GitHub", "REST APIs", "CI/CD", "Reproducible Pipelines",
                "Model Serving", "Streamlit", "Jupyter",
            ],
        ),
        SkillCategory(
            name="Core CS",
            skills=["Data Structures", "Algorithms", "Operating Systems", "DBMS", "System Design"],
        ),
    ]

    education = [
        Education(
            degree="B.Tech, Computer Science & Engineering (AI Specialization)",
            institution="Noida Institute of Engineering & Technology",
            location="Greater Noida",
            start_date=date(2021, 11, 1),
            end_date=date(2025, 6, 30),
            is_current=False,
        ),
        Education(
            degree="Intermediate & High School",
            institution="Udai Pratap Inter College",
            location="Varanasi, UP",
            start_date=date(2017, 3, 1),
            end_date=date(2020, 6, 30),
            is_current=False,
        ),
    ]

    location_preferences = LocationPreferences(
        current_location="Gurugram, Haryana, India",
        primary=[
            "Gurugram", "Gurgaon", "Cyber Hub", "DLF Cyber City", "Udyog Vihar",
            "Golf Course Road", "Sector 18 Gurugram", "Sector 19 Gurugram",
            "Sector 20 Gurugram", "Sector 21 Gurugram", "Sector 24 Gurugram",
            "Sector 25 Gurugram", "Sector 30 Gurugram", "Remote India",
        ],
        secondary=["Noida", "Greater Noida", "Delhi", "Delhi NCR", "Faridabad"],
        remote=[
            "India remote", "Global remote", "US remote", "Europe remote",
            "UK remote", "APAC remote", "Remote contract", "Remote freelance",
        ],
        will_relocate=False,
    )

    availability = Availability(
        current_employment="Full-time",
        open_to_part_time=True,
        open_to_contract=True,
        open_to_freelance=True,
        open_to_remote=True,
        preferred_schedules=[
            "evening (6PM-2AM IST)",
            "evening (8PM-2AM IST)",
            "night (10PM-6AM IST)",
            "weekend",
            "async",
            "10-20 hours/week",
            "20-30 hours/week",
        ],
    )

    work_authorizations = [
        WorkAuthorization(country="India", status="Citizen", requires_sponsorship=False),
    ]

    tier1 = [
        "AI Engineer", "Machine Learning Engineer", "ML Engineer", "Generative AI Engineer",
        "LLM Engineer", "Applied AI Engineer", "AI/ML Engineer", "Software Engineer - AI",
        "Software Engineer - ML", "Backend Engineer - AI", "Python Software Engineer",
        "AI Agent Engineer", "Agentic AI Engineer", "Research Engineer", "ML Platform Engineer",
        "AI Infrastructure Engineer", "Evaluation Engineer", "Model Evaluation Engineer",
        "AI Safety Engineer", "AI Data Engineer", "AI Training Engineer", "AI Coding Agent Engineer",
    ]
    tier2 = [
        "Software Engineer", "Backend Engineer", "Full Stack Engineer", "Python Developer",
        "Java Developer", "Data Engineer", "Data Analyst", "ML Data Scientist", "Data Scientist",
        "Automation Engineer", "Developer Tools Engineer", "QA Automation Engineer", "AI QA Engineer",
    ]
    tier3 = [
        "AI Trainer", "AI Evaluator", "LLM Evaluator", "RLHF Contributor", "SFT Contributor",
        "AI Coding Evaluator", "AI Benchmark Contributor", "AI Research Contributor",
        "Freelance AI Engineer", "Freelance ML Engineer", "AI Expert Contributor",
    ]

    priority_companies = [
        "OpenAI", "Anthropic", "Google", "Google DeepMind", "Microsoft", "Meta", "NVIDIA",
        "Amazon", "AWS", "Apple", "xAI", "Mistral AI", "Cohere", "Perplexity", "Hugging Face",
        "Scale AI", "Databricks", "Snowflake", "Cursor", "Anysphere", "Replit", "Together AI",
        "Groq", "ElevenLabs", "LangChain", "Weights & Biases", "OpenRouter", "Fireworks AI",
        "Replicate", "Handshake AI", "Surge AI", "TELUS Digital AI", "Outlier",
    ]

    hard_pass_terms = [
        "MLM", "network marketing", "multi-level marketing", "pay to apply", "registration fee",
        "training fee required", "pyramid", "bitcoin investment", "crypto investor",
        "nurse", "driver", "chef", "cook", "medical representative", "accountant",
        "sales executive (field)", "field sales", "door-to-door", "insurance agent",
    ]

    resume_variants = [
        ResumeVariant(
            name="ai_ml",
            target_roles=["AI Engineer", "ML Engineer", "LLM Engineer", "Applied AI Engineer", "Generative AI Engineer"],
            file_path=resume_root / "harshaksh_singh_resume_ai_ml.pdf",
            description="Primary ML/LLM/RLHF resume (Ethara AI, Project Dynamo, Multi-SWE-bench, Harbor, Turing, Outlier)",
            highlighted_skills=["LLM Fine-tuning", "RLHF", "RAG", "PyTorch", "Docker", "Benchmark Design", "SFT", "LoRA"],
        ),
        ResumeVariant(
            name="software_engineer",
            target_roles=["Software Engineer", "Backend Engineer", "Python Developer", "Full Stack Engineer"],
            file_path=resume_root / "harshaksh_singh_resume_software_engineer.pdf",
            description="Software engineering focus (Python/Java/REST APIs/Docker/Git)",
            highlighted_skills=["Python", "Java", "REST APIs", "Docker", "Git", "CI/CD", "System Design"],
        ),
        ResumeVariant(
            name="ai_evaluation",
            target_roles=["AI Evaluator", "LLM Evaluator", "Evaluation Engineer", "Model Evaluation Engineer", "AI Trainer"],
            file_path=resume_root / "harshaksh_singh_resume_ai_evaluation.pdf",
            description="AI evaluation / benchmarking focus (Handshake AI Dynamo, Multi-SWE-bench, Harbor, Turing, Outlier)",
            highlighted_skills=[
                "Benchmark Design", "Evaluation Rubrics", "Verifier Design", "RLHF", "SFT",
                "Model Evaluation", "pytest", "Gold Solutions",
            ],
        ),
        ResumeVariant(
            name="part_time_remote",
            target_roles=["Part-time AI Engineer", "Freelance AI Engineer", "Contract ML Engineer", "Remote AI Engineer"],
            file_path=resume_root / "harshaksh_singh_resume_part_time.pdf",
            description="Part-time / freelance focus emphasizing async contractor experience across frontier AI platforms",
            highlighted_skills=["RLHF", "SFT", "AI Evaluation", "Remote collaboration", "Async contractor"],
        ),
    ]

    return Profile(
        full_name="Harshaksh Singh",
        headline="Machine Learning Engineer — LLM Training, RLHF, RAG & Frontier AI Benchmarking",
        email="harshakshsingh1010@gmail.com",
        phone="+91 8303818640",
        location="Gurugram, Haryana, India",
        linkedin_url=None,
        github_url=None,
        portfolio_url=None,
        summary=(
            "Machine Learning Engineer specializing in the AI training-data trajectory: "
            "LLM fine-tuning (SFT/LoRA) and RLHF, benchmark task authoring, evaluation rubric design, "
            "and reproducible Dockerized ML pipelines. Selected contributor at Handshake AI (Project Dynamo) "
            "and active across frontier AI data platforms — Multi-SWE-bench, Harbor Benchmark, Turing, "
            "and Outlier AI — designing tasks and gold reference solutions that evaluate how state-of-the-art "
            "models code, reason, and fail. Strong engineering core: Python, PyTorch, RAG pipelines, REST APIs, "
            "Git/GitHub, CI/CD. B.Tech in Computer Science (AI Specialization)."
        ),
        experiences=experiences,
        projects=projects,
        skill_categories=skill_categories,
        education=education,
        languages_spoken=["Hindi", "English", "Maithili"],
        location_preferences=location_preferences,
        availability=availability,
        work_authorizations=work_authorizations,
        tier1_target_roles=tier1,
        tier2_target_roles=tier2,
        tier3_target_roles=tier3,
        hard_pass_terms=hard_pass_terms,
        priority_companies=priority_companies,
        excluded_companies=[],
        resume_variants=resume_variants,
    )
