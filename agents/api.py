"""
FastAPI REST API Server for Ki67 Proliferation Indexer.
"""
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from ki67_indexer import calculate_index
from .base import AuditLogger, PHIGuard, SecurityException
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Ki67 Proliferation Indexer API",
    description="Count-based Ki-67 index and separately labeled legacy audit workflow",
    version="3.0.1",
)


class ChatRequest(BaseModel):
    query: str


class CountRequest(BaseModel):
    positive_cells: int = Field(ge=0, strict=True)
    total_cells: int = Field(gt=0, strict=True)


@app.get("/", include_in_schema=False)
def index_page():
    file_path = Path(__file__).resolve().parent.parent / "web" / "index.html"
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Web interface is not installed.")
    return FileResponse(file_path, media_type="text/html")


@app.post("/api/ki67")
def api_ki67(payload: CountRequest):
    try:
        return calculate_index(payload.positive_cells, payload.total_cells)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "ki67-proliferation-indexer", "domain": "Clinical & Biomedical AI", "version": "3.0.1"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    try:
        dossier = supervisor.process_task(payload)
    except SecurityException as exc:
        raise HTTPException(status_code=422, detail="Potential patient identifier detected; use non-identifying codes.") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Audit service is not configured.") from exc
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/audit/logs")
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
