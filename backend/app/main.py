import base64
import io
import uuid
from csv import DictWriter
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.auth import get_current_user
from app.core.config import get_settings
from app.core.db import get_db
from app.models import ChangeType, Comparison, ImpactFinding, ImportBatch, Project, RequirementChange, RequirementSnapshot, ReviewStatus, Severity
from app.schemas.api import ComparisonCreate, ExportOut, FindingReview, ImportRequest, ImportOut, ProjectCreate, ProjectOut, UserContext
from app.services.compare import build_comparison
from app.services.csv_import import normalize_rows, parse_csv, source_hash, suggest_mapping, validate_rows
from app.services.pdf_report import build_requirements_impact_pdf
from app.integrations.billing import BillingService

settings = get_settings()
if settings.sentry_dsn:
    import sentry_sdk

    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.05)
app = FastAPI(title="Requirements Impact Radar API")
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin, "http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
if settings.app_env == "production":
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request.state.request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["x-request-id"] = request.state.request_id
    response.headers["x-content-type-options"] = "nosniff"
    response.headers["x-frame-options"] = "DENY"
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content={"error": detail, "request_id": request.state.request_id})


def scoped_project(db: Session, project_id: uuid.UUID, user: UserContext) -> Project:
    project = db.scalar(select(Project).where(Project.id == project_id, Project.workspace_id == user.workspace_id))
    if project is None:
        raise HTTPException(status_code=404, detail={"message": "Project was not found."})
    return project


def import_out(batch: ImportBatch) -> dict:
    return {"id": str(batch.id), "filename": batch.filename, "version_label": batch.version_label, "row_count": batch.row_count, "status": batch.status}


def comparison_out(comparison: Comparison) -> dict:
    return {"id": str(comparison.id), "project_id": str(comparison.project_id), "baseline_import_id": str(comparison.baseline_import_id), "comparison_import_id": str(comparison.comparison_import_id), "status": comparison.status, "summary_json": comparison.summary_json or {}, "created_at": comparison.created_at.isoformat() if comparison.created_at else None}


def change_out(change: RequirementChange) -> dict:
    return {"id": str(change.id), "comparison_id": str(change.comparison_id), "external_id": change.external_id, "change_type": change.change_type.value, "old_snapshot_id": str(change.old_snapshot_id) if change.old_snapshot_id else None, "new_snapshot_id": str(change.new_snapshot_id) if change.new_snapshot_id else None, "changed_fields": change.changed_fields or {}, "text_diff": change.text_diff}


def finding_out(finding: ImpactFinding) -> dict:
    return {"id": str(finding.id), "requirement_change_id": str(finding.requirement_change_id), "impacted_requirement_external_id": finding.impacted_requirement_external_id, "severity": finding.severity.value, "confidence": finding.confidence, "impact_score": finding.impact_score, "detection_method": finding.detection_method, "reason": finding.reason, "relationship_type": finding.relationship_type, "review_status": finding.review_status.value, "reviewer_note": finding.reviewer_note}


@app.get("/health")
def health() -> dict:
    return {"ok": True, "ai_provider": settings.ai_provider, "billing_enabled": settings.billing_enabled}


@app.get("/me")
def me(user: UserContext = Depends(get_current_user)) -> UserContext:
    return user


@app.get("/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), user: UserContext = Depends(get_current_user)):
    projects = db.scalars(select(Project).where(Project.workspace_id == user.workspace_id).order_by(Project.created_at.desc())).all()
    output = []
    for project in projects:
        req_count = db.scalar(select(func.count()).select_from(RequirementSnapshot).where(RequirementSnapshot.project_id == project.id)) or 0
        changed = db.scalar(select(func.count()).select_from(RequirementChange).join(Comparison, RequirementChange.comparison_id == Comparison.id).where(Comparison.project_id == project.id, RequirementChange.change_type != ChangeType.UNCHANGED)) or 0
        unresolved = db.scalar(select(func.count()).select_from(ImpactFinding).join(RequirementChange).join(Comparison).where(Comparison.project_id == project.id, ImpactFinding.review_status == ReviewStatus.UNREVIEWED)) or 0
        output.append(ProjectOut(id=project.id, name=project.name, description=project.description, requirements_count=req_count, changed_requirements=changed, unresolved_findings=unresolved))
    return output


@app.post("/projects", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db), user: UserContext = Depends(get_current_user)):
    existing = db.scalar(select(func.count()).select_from(Project).where(Project.workspace_id == user.workspace_id)) or 0
    if existing >= 1:
        raise HTTPException(status_code=403, detail={"message": "The FREE plan allows 1 project. Upgrade to create more projects."})
    project = Project(workspace_id=user.workspace_id, name=payload.name, description=payload.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return ProjectOut(id=project.id, name=project.name, description=project.description)


@app.get("/projects/{project_id}")
def get_project(project_id: uuid.UUID, db: Session = Depends(get_db), user: UserContext = Depends(get_current_user)):
    project = scoped_project(db, project_id, user)
    imports = db.scalars(select(ImportBatch).where(ImportBatch.project_id == project.id).order_by(ImportBatch.imported_at)).all()
    comparisons = db.scalars(select(Comparison).where(Comparison.project_id == project.id).order_by(Comparison.created_at.desc())).all()
    return {"project": {"id": str(project.id), "name": project.name, "description": project.description}, "imports": [import_out(item) for item in imports], "comparisons": [comparison_out(item) for item in comparisons]}


@app.post("/imports/preview")
async def preview_import(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > settings.upload_limit_bytes:
        raise HTTPException(status_code=413, detail={"message": "CSV files must be 10 MB or smaller."})
    if not file.filename.lower().endswith(".csv") or file.content_type not in {"text/csv", "application/vnd.ms-excel", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail={"message": "Radar imports CSV files only."})
    text = data.decode("utf-8-sig")
    parsed = parse_csv(text)
    mapping = suggest_mapping(parsed.columns)
    warnings = parsed.warnings + validate_rows(parsed.rows, mapping) if mapping else parsed.warnings
    return {"columns": parsed.columns, "suggested_mapping": mapping, "preview_rows": parsed.rows[:10], "warnings": warnings, "csv_text": text}


@app.post("/projects/{project_id}/imports", response_model=ImportOut)
def create_import(project_id: uuid.UUID, payload: ImportRequest, db: Session = Depends(get_db), user: UserContext = Depends(get_current_user)):
    project = scoped_project(db, project_id, user)
    parsed = parse_csv(payload.csv_text)
    warnings = validate_rows(parsed.rows, payload.mapping)
    fatal = [w for w in warnings if "required" in w or "missing a Requirement ID" in w or "Duplicate Requirement IDs" in w]
    if fatal:
        raise HTTPException(status_code=400, detail={"message": "Radar could not import the file.", "warnings": warnings})
    rows = normalize_rows(parsed.rows, payload.mapping)
    import_count = db.scalar(select(func.count()).select_from(ImportBatch).where(ImportBatch.project_id == project.id)) or 0
    if import_count >= 2:
        raise HTTPException(status_code=403, detail={"message": "The FREE plan allows 2 imports per project."})
    if len(rows) > 250:
        raise HTTPException(status_code=403, detail={"message": "The FREE plan allows up to 250 requirements per project."})
    batch = ImportBatch(project_id=project.id, filename=payload.filename, version_label=payload.version_label, row_count=len(rows), source_hash=source_hash(payload.csv_text), mapping_json=payload.mapping, status="COMPLETE")
    db.add(batch)
    db.flush()
    db.bulk_save_objects([RequirementSnapshot(project_id=project.id, import_batch_id=batch.id, **row) for row in rows])
    db.commit()
    db.refresh(batch)
    return batch


@app.post("/projects/{project_id}/comparisons")
def create_comparison(project_id: uuid.UUID, payload: ComparisonCreate, db: Session = Depends(get_db), user: UserContext = Depends(get_current_user)):
    project = scoped_project(db, project_id, user)
    for import_id in [payload.baseline_import_id, payload.comparison_import_id]:
        if db.scalar(select(ImportBatch).where(ImportBatch.id == import_id, ImportBatch.project_id == project.id)) is None:
            raise HTTPException(status_code=404, detail={"message": "Import version was not found for this project."})
    comparison = Comparison(project_id=project.id, baseline_import_id=payload.baseline_import_id, comparison_import_id=payload.comparison_import_id, status="COMPARING", summary_json={})
    db.add(comparison)
    db.commit()
    db.refresh(comparison)
    build_comparison(db, comparison)
    db.refresh(comparison)
    return comparison_out(comparison)


@app.get("/projects/{project_id}/comparisons/{comparison_id}")
def get_comparison(project_id: uuid.UUID, comparison_id: uuid.UUID, db: Session = Depends(get_db), user: UserContext = Depends(get_current_user)):
    scoped_project(db, project_id, user)
    comparison = db.scalar(select(Comparison).where(Comparison.id == comparison_id, Comparison.project_id == project_id))
    if comparison is None:
        raise HTTPException(status_code=404, detail={"message": "Comparison was not found."})
    changes = db.scalars(select(RequirementChange).where(RequirementChange.comparison_id == comparison.id).order_by(RequirementChange.external_id)).all()
    findings = db.scalars(select(ImpactFinding).join(RequirementChange).where(RequirementChange.comparison_id == comparison.id)).all()
    return {"comparison": comparison_out(comparison), "changes": [change_out(item) for item in changes], "findings": [finding_out(item) for item in findings]}


@app.patch("/findings/{finding_id}")
def review_finding(finding_id: uuid.UUID, payload: FindingReview, db: Session = Depends(get_db), user: UserContext = Depends(get_current_user)):
    finding = db.scalar(select(ImpactFinding).join(RequirementChange).join(Comparison).join(Project, Comparison.project_id == Project.id).where(ImpactFinding.id == finding_id, Project.workspace_id == user.workspace_id))
    if finding is None:
        raise HTTPException(status_code=404, detail={"message": "Finding was not found."})
    if payload.review_status:
        finding.review_status = ReviewStatus(payload.review_status)
    if payload.severity:
        finding.manually_adjusted_severity = Severity(payload.severity)
        finding.severity = Severity(payload.severity)
    if payload.reviewer_note is not None:
        finding.reviewer_note = payload.reviewer_note
    db.commit()
    db.refresh(finding)
    return finding_out(finding)


def safe_csv(value: object) -> object:
    if isinstance(value, str) and value[:1] in ["=", "+", "-", "@"]:
        return "'" + value
    return value


@app.get("/projects/{project_id}/comparisons/{comparison_id}/export.csv", response_model=ExportOut)
def export_csv(project_id: uuid.UUID, comparison_id: uuid.UUID, db: Session = Depends(get_db), user: UserContext = Depends(get_current_user)):
    scoped_project(db, project_id, user)
    findings = db.scalars(select(ImpactFinding).join(RequirementChange).join(Comparison).where(Comparison.id == comparison_id, Comparison.project_id == project_id)).all()
    output = io.StringIO()
    fields = ["Changed Requirement", "Change Type", "Impacted Requirement", "Severity", "Confidence", "Reason", "Detection Method", "Review Status", "Reviewer Note"]
    writer = DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for finding in findings:
        writer.writerow({k: safe_csv(v) for k, v in {"Changed Requirement": finding.change.external_id, "Change Type": finding.change.change_type.value, "Impacted Requirement": finding.impacted_requirement_external_id, "Severity": finding.severity.value, "Confidence": round(finding.confidence, 2), "Reason": finding.reason, "Detection Method": finding.detection_method, "Review Status": finding.review_status.value, "Reviewer Note": finding.reviewer_note or ""}.items()})
    return ExportOut(filename="radar-comparison.csv", content_base64=base64.b64encode(output.getvalue().encode()).decode(), media_type="text/csv")


@app.get("/projects/{project_id}/comparisons/{comparison_id}/export.pdf", response_model=ExportOut)
def export_pdf(project_id: uuid.UUID, comparison_id: uuid.UUID, db: Session = Depends(get_db), user: UserContext = Depends(get_current_user)):
    project = scoped_project(db, project_id, user)
    comparison = db.scalar(select(Comparison).where(Comparison.id == comparison_id, Comparison.project_id == project_id))
    if comparison is None:
        raise HTTPException(status_code=404, detail={"message": "Comparison was not found."})
    imports = db.scalars(select(ImportBatch).where(ImportBatch.project_id == project.id).order_by(ImportBatch.imported_at)).all()
    changes = db.scalars(select(RequirementChange).where(RequirementChange.comparison_id == comparison_id).order_by(RequirementChange.external_id)).all()
    findings = db.scalars(select(ImpactFinding).join(RequirementChange).where(RequirementChange.comparison_id == comparison_id).order_by(ImpactFinding.severity, RequirementChange.external_id, ImpactFinding.impacted_requirement_external_id)).all()
    pdf_bytes = build_requirements_impact_pdf(project, comparison, imports, changes, findings)
    return ExportOut(filename="radar-comparison.pdf", content_base64=base64.b64encode(pdf_bytes).decode(), media_type="application/pdf")


@app.post("/billing/webhook")
async def paddle_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("paddle-signature")
    billing = BillingService(settings.paddle_webhook_secret)
    if settings.billing_enabled and settings.paddle_webhook_secret and not billing.verify_webhook(body, signature):
        raise HTTPException(status_code=400, detail={"message": "Invalid Paddle webhook signature."})
    return {"ok": True, "processed": settings.billing_enabled, "bytes": len(body)}
