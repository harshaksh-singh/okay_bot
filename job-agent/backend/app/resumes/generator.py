from __future__ import annotations

from pathlib import Path

from app.profile.schema import Profile, ResumeVariant


def _header(profile: Profile) -> list[str]:
    return [
        profile.full_name,
        profile.headline,
        f"{profile.email} · {profile.phone} · {profile.location}",
        "",
    ]


def _experience_block(profile: Profile) -> list[str]:
    out = ["EXPERIENCE", ""]
    for e in profile.experiences:
        dates = f"{e.start_date.strftime('%b %Y')} – {e.end_date.strftime('%b %Y') if e.end_date else 'Present'}"
        out.append(f"{e.role} — {e.company} ({dates}, {e.location}, {e.employment_type})")
        for b in e.bullets:
            out.append(f"  • {b}")
        out.append("")
    return out


def _projects_block(profile: Profile) -> list[str]:
    out = ["PROJECTS", ""]
    for p in profile.projects:
        out.append(f"{p.name} ({p.date_range}) — {', '.join(p.tech_stack)}")
        for b in p.bullets:
            out.append(f"  • {b}")
        out.append("")
    return out


def _skills_block(profile: Profile, highlighted: list[str] | None = None) -> list[str]:
    out = ["SKILLS", ""]
    if highlighted:
        out.append(f"Highlighted for this variant: {', '.join(highlighted)}")
        out.append("")
    for cat in profile.skill_categories:
        out.append(f"{cat.name}: {', '.join(cat.skills)}")
    out.append("")
    return out


def _education_block(profile: Profile) -> list[str]:
    out = ["EDUCATION", ""]
    for e in profile.education:
        dates = f"{e.start_date.strftime('%b %Y')} – {e.end_date.strftime('%b %Y')}"
        out.append(f"{e.degree} — {e.institution}, {e.location} ({dates})")
    out.append("")
    return out


def _summary_block(profile: Profile) -> list[str]:
    return ["PROFESSIONAL SUMMARY", "", profile.summary, ""]


def render_variant_text(profile: Profile, variant: ResumeVariant) -> str:
    lines: list[str] = []
    lines.extend(_header(profile))
    lines.append(f"[Variant: {variant.name}] {variant.description}")
    lines.append("")
    lines.extend(_summary_block(profile))
    lines.extend(_experience_block(profile))
    lines.extend(_projects_block(profile))
    lines.extend(_skills_block(profile, highlighted=variant.highlighted_skills))
    lines.extend(_education_block(profile))
    if profile.languages_spoken:
        lines.append("LANGUAGES: " + ", ".join(profile.languages_spoken))
    return "\n".join(lines) + "\n"


class ResumeGenerator:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render_all(self, profile: Profile) -> dict[str, Path]:
        out: dict[str, Path] = {}
        for v in profile.resume_variants:
            path = self.output_dir / f"resume_{v.name}.txt"
            path.write_text(render_variant_text(profile, v))
            out[v.name] = path
        return out

    def ensure_variant(self, profile: Profile, variant_name: str) -> Path | None:
        v = next((x for x in profile.resume_variants if x.name == variant_name), None)
        if not v:
            return None
        path = self.output_dir / f"resume_{v.name}.txt"
        if not path.exists():
            path.write_text(render_variant_text(profile, v))
        return path
