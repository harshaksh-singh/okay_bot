from __future__ import annotations

from app.profile import FactSource


def test_profile_identity_fields(profile):
    assert profile.full_name == "Harshaksh Singh"
    assert str(profile.email) == "harshakshsingh1010@gmail.com"
    assert profile.phone == "+91 8303818640"
    assert "Gurugram" in profile.location


def test_profile_has_current_ethara_ai_role(profile):
    current = [e for e in profile.experiences if e.is_current]
    assert any(e.company == "Ethara AI" for e in current)
    ethara = next(e for e in profile.experiences if e.company == "Ethara AI")
    assert ethara.role == "Software Engineer"
    assert ethara.start_date.year == 2025
    assert ethara.end_date is None


def test_profile_contractor_platforms(profile):
    contractor_companies = {e.company for e in profile.experiences if e.employment_type == "Independent Contractor"}
    for name in ["Handshake AI (Project Dynamo)", "Multi-SWE-bench", "Harbor Benchmark", "Turing", "Outlier AI"]:
        assert name in contractor_companies, f"missing contractor platform: {name}"


def test_profile_education_niet(profile):
    niet = next((e for e in profile.education if "Noida Institute" in e.institution), None)
    assert niet is not None
    assert "AI" in niet.degree
    assert niet.start_date.year == 2021
    assert niet.end_date.year == 2025


def test_profile_target_roles_cover_ai_ml_llm(profile):
    all_roles = profile.all_target_roles
    for must in ["ai engineer", "machine learning engineer", "llm engineer"]:
        assert must in all_roles


def test_profile_facts_list_includes_identity(profile):
    facts = profile.to_fact_list()
    keys = [f.key for f in facts]
    assert "name" in keys and "email" in keys and "phone" in keys
    assert all(f.source == FactSource.PROFILE_FACT for f in facts)


def test_profile_resume_variants_exist(profile):
    names = {v.name for v in profile.resume_variants}
    assert {"ai_ml", "software_engineer", "ai_evaluation", "part_time_remote"}.issubset(names)


def test_profile_hard_pass_terms_present(profile):
    hp = {t.lower() for t in profile.hard_pass_terms}
    assert "mlm" in hp
    assert any("pay to apply" in t or "pay to apply" in t.lower() for t in profile.hard_pass_terms)


def test_profile_priority_companies_include_anthropic_openai(profile):
    pc = {c.lower() for c in profile.priority_companies}
    assert "anthropic" in pc
    assert "openai" in pc
    assert "handshake ai" in pc
