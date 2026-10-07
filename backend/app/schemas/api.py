from uuid import UUID
from pydantic import BaseModel, Field


class UserContext(BaseModel):
    user_id: str
    workspace_id: UUID
    workspace_name: str


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""


class ProjectOut(BaseModel):
    id: UUID
    name: str
    description: str
    requirements_count: int = 0
    changed_requirements: int = 0
    unresolved_findings: int = 0


class MappingPreview(BaseModel):
    columns: list[str]
    suggested_mapping: dict[str, str]
    preview_rows: list[dict]
    warnings: list[str]


class ImportRequest(BaseModel):
    filename: str
    version_label: str
    csv_text: str
    mapping: dict[str, str]


class ImportOut(BaseModel):
    id: UUID
    filename: str
    version_label: str
    row_count: int
    status: str


class ComparisonCreate(BaseModel):
    baseline_import_id: UUID
    comparison_import_id: UUID


class FindingReview(BaseModel):
    review_status: str | None = None
    severity: str | None = None
    reviewer_note: str | None = None


class ExportOut(BaseModel):
    filename: str
    content_base64: str
    media_type: str


class FeedbackCreate(BaseModel):
    feedback_type: str = Field(pattern="^(Bug|Confusing|Idea)$")
    message: str = Field(min_length=1, max_length=4000)
    screen: str = Field(default="", max_length=120)


class FeedbackOut(BaseModel):
    id: UUID
    feedback_type: str
    screen: str
