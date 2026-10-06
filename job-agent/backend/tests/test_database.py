from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database.engine import Base
from app.database.models import ApplicationRow, CompanyRow, JobRow


@pytest.fixture()
def inmem_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    with Session() as s:
        yield s


def test_can_insert_and_read_company(inmem_session):
    c = CompanyRow(canonical_name="anthropic", name="Anthropic", is_priority=True, priority_score=100)
    inmem_session.add(c)
    inmem_session.commit()
    row = inmem_session.scalars(select(CompanyRow).where(CompanyRow.canonical_name == "anthropic")).one()
    assert row.name == "Anthropic"
    assert row.is_priority
    assert row.priority_score == 100


def test_can_insert_and_read_job(inmem_session):
    j = JobRow(
        job_id="abc123",
        source="mock",
        source_job_id="src-1",
        company_name="Anthropic",
        title="AI Engineer",
        location="Remote",
        remote="remote_global",
        employment_type="full_time",
        description="test",
    )
    inmem_session.add(j)
    inmem_session.commit()
    row = inmem_session.scalars(select(JobRow).where(JobRow.job_id == "abc123")).one()
    assert row.title == "AI Engineer"


def test_application_has_foreign_key(inmem_session):
    j = JobRow(job_id="xyz", source="mock", company_name="X", title="Y", description="")
    inmem_session.add(j); inmem_session.commit()
    a = ApplicationRow(application_id="app_x", job_id="xyz", status="DISCOVERED")
    inmem_session.add(a); inmem_session.commit()
    row = inmem_session.scalars(select(ApplicationRow).where(ApplicationRow.application_id == "app_x")).one()
    assert row.job_id == "xyz"


def test_unique_source_source_job_id_constraint(inmem_session):
    j1 = JobRow(job_id="k1", source="mock", source_job_id="S1", company_name="A", title="T", description="")
    inmem_session.add(j1); inmem_session.commit()
    j2 = JobRow(job_id="k2", source="mock", source_job_id="S1", company_name="A", title="T2", description="")
    inmem_session.add(j2)
    with pytest.raises(Exception):
        inmem_session.commit()
