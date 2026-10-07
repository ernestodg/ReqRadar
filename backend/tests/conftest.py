import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://radar:radar@localhost:5432/radar")
os.environ.setdefault("DEV_AUTH_BYPASS", "true")

from app.core.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Comparison, Feedback, ImpactFinding, ImportBatch, Project, RequirementChange, RequirementSnapshot, Workspace  # noqa: E402


@pytest.fixture()
def client():
    with SessionLocal() as db:
        for model in [Feedback, ImpactFinding, RequirementChange, Comparison, RequirementSnapshot, ImportBatch, Project, Workspace]:
            db.execute(delete(model))
        db.commit()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def user_headers():
    return {"x-dev-user-id": f"test-user-{uuid.uuid4()}"}


def sample_mapping() -> dict[str, str]:
    return {
        "Requirement ID": "Requirement ID",
        "Type": "Type",
        "Title": "Title",
        "Description": "Description",
        "Status": "Status",
        "Parent ID": "Parent ID",
        "Related To": "Related To",
        "Tags": "Tags",
        "Owner": "Owner",
    }
