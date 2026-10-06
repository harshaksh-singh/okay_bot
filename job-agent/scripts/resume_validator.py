from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.profile import get_profile  # noqa: E402

_PLACEHOLDER_PATTERNS = [
    re.compile(r"placeholder", re.I),
    re.compile(r"lorem ipsum", re.I),
    re.compile(r"\[.*(?:name|email|phone|replace|insert).*\]", re.I),
    re.compile(r"\byour\s+(name|email|phone|experience|skills|employer)\b", re.I),
]

_FORBIDDEN_CLAIMS = [
    re.compile(r"\b(10|15|20)\+?\s*years?\b", re.I),
    re.compile(r"\bphd\b", re.I),
    re.compile(r"\bmba\b", re.I),
    re.compile(r"\bprincipal engineer\b", re.I),
    re.compile(r"\bstaff engineer\b", re.I),
    re.compile(r"\bus citizen\b", re.I),
    re.compile(r"\bgreen card\b", re.I),
    re.compile(r"\bstanford\b", re.I),
    re.compile(r"\bharvard\b", re.I),
]


def _try_extract_pdf(path: Path) -> str:
    try:
        import pypdf
        reader = pypdf.PdfReader(path)
        parts = [p.extract_text() or "" for p in reader.pages]
        return "\n".join(parts)
    except ImportError:
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                return "\n".join(p.extract_text() or "" for p in pdf.pages)
        except Exception:
            return ""
    except Exception:
        return ""


def validate_resume(path: Path, profile_facts: set[str], required_phrases: set[str]) -> dict:
    report: dict = {"path": str(path), "status": "OK", "issues": []}
    if not path.exists():
        return {"path": str(path), "status": "MISSING", "issues": ["file not found"]}
    if path.suffix.lower() == ".pdf":
        text = _try_extract_pdf(path)
        if not text:
            report["issues"].append("could not extract text (pypdf/pdfplumber not installed, or PDF is image-only)")
    else:
        try:
            text = path.read_text(errors="ignore")
        except Exception as e:
            return {"path": str(path), "status": "ERROR", "issues": [f"read failed: {e}"]}

    if not text or len(text.strip()) < 100:
        report["issues"].append(f"extracted text too short ({len(text.strip())} chars)")

    lower = text.lower()
    for p in _PLACEHOLDER_PATTERNS:
        if p.search(text):
            report["issues"].append(f"placeholder pattern matched: {p.pattern}")

    for p in _FORBIDDEN_CLAIMS:
        hit = p.search(text)
        if not hit:
            continue
        matched = hit.group(0).lower()
        if any(matched in f.lower() for f in profile_facts):
            continue
        report["issues"].append(f"forbidden/un-grounded claim: {hit.group(0)}")

    required_missing = [r for r in required_phrases if r.lower() not in lower]
    if required_missing:
        report["issues"].append(f"missing required profile phrases: {required_missing}")

    import re as _re
    email_hit = _re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    if not email_hit:
        report["issues"].append("missing email contact")
    phone_hit = _re.search(r"\+?\d[\d\s\-()]{7,}", text)
    if not phone_hit:
        report["issues"].append("missing phone contact")

    standard_section_names = ["experience", "education", "skill"]
    section_hits = [name for name in standard_section_names if name in lower]
    if len(section_hits) < 2:
        report["issues"].append(f"formatting: expected at least 2 standard sections (experience/education/skills), found: {section_hits}")

    report["status"] = "FAIL" if report["issues"] else "OK"
    report["found_contact_email"] = bool(email_hit)
    report["found_contact_phone"] = bool(phone_hit)
    report["sections_detected"] = section_hits
    return report


def main() -> int:
    profile = get_profile()
    required = {profile.full_name, "Ethara AI"}
    for exp in profile.experiences:
        required.add(exp.company)
    for edu in profile.education:
        required.add(edu.institution.split(",")[0])

    required_minimal = {profile.full_name, "Ethara AI"}
    profile_fact_strings = {str(f.value) for f in profile.to_fact_list()}

    candidates: list[Path] = []
    resumes_dir = REPO_ROOT / "resumes"
    if resumes_dir.exists():
        for p in sorted(resumes_dir.iterdir()):
            if p.suffix.lower() in {".pdf", ".txt", ".md"}:
                candidates.append(p)

    gen_dir = REPO_ROOT / "data" / "resumes_generated"
    if gen_dir.exists():
        for p in sorted(gen_dir.iterdir()):
            if p.suffix.lower() in {".txt", ".md", ".pdf"}:
                candidates.append(p)

    print("=== Resume validation ===")
    print(f"profile: {profile.full_name}")
    print(f"required phrases: {sorted(required_minimal)}")
    print()
    all_ok = True
    for c in candidates:
        rep = validate_resume(c, profile_fact_strings, required_minimal)
        print(f"{rep['status']:8s} {rep['path']}")
        for i in rep["issues"]:
            print(f"         - {i}")
            all_ok = all_ok and False
    if not candidates:
        print("INFO     no resume files found under resumes/ or data/resumes_generated/")
        print("         place real PDFs under resumes/ before pre-approved submission")
    print()
    print("Status: " + ("PASS" if all_ok else "FAIL"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
