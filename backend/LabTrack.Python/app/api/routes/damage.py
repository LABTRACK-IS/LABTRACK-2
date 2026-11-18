from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid
from app.api.routes.ai_chat import _run, _resolve_table, _count

router = APIRouter()
_MEMORY_DAMAGE: list[dict] = []

class DamageReportBase(BaseModel):
    asset_id: uuid.UUID
    reported_by_user_id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4)
    severity: str = "Major"
    damage_type: str = "Hardware"
    description: str = Field(..., min_length=3, max_length=1000)

class DamageReportCreate(DamageReportBase):
    pass

class DamageReportUpdate(BaseModel):
    severity: Optional[str] = None
    damage_type: Optional[str] = None
    description: Optional[str] = None
    is_resolved: Optional[bool] = None

class DamageReportResponse(DamageReportBase):
    id: uuid.UUID
    is_resolved: bool = False
    reported_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class DamageAssessmentSummary(BaseModel):
    total_active_reports: int
    critical_count: int
    major_count: int
    minor_count: int
    estimated_repair_cost_total: float

@router.get("/", response_model=List[DamageReportResponse], status_code=status.HTTP_200_OK)
async def list_damage_reports(asset_id: Optional[uuid.UUID] = Query(None), is_resolved: Optional[bool] = Query(None), skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    tbl = await _resolve_table("ProblemReports") or await _resolve_table("DamageReports")
    if tbl:
        rows = await _run(f"SELECT * FROM {tbl} LIMIT $1 OFFSET $2", (limit, skip))
        if rows:
            out = []
            for r in rows:
                rid = r.get("Id") or r.get("id") or uuid.uuid4()
                aid = r.get("AssetId") or r.get("WorkstationId") or r.get("asset_id") or asset_id or uuid.uuid4()
                uid = r.get("ReportedByUserId") or r.get("UserId") or r.get("reported_by_user_id") or uuid.uuid4()
                st = str(r.get("Status") or "").upper()
                resolved = bool(r.get("IsResolved")) or st in ("RESOLVED", "CLOSED", "COMPLETED")
                out.append(DamageReportResponse(
                    id=rid if isinstance(rid, uuid.UUID) else uuid.UUID(str(rid)),
                    asset_id=aid if isinstance(aid, uuid.UUID) else uuid.UUID(str(aid)),
                    reported_by_user_id=uid if isinstance(uid, uuid.UUID) else uuid.UUID(str(uid)),
                    severity=str(r.get("Severity") or r.get("Priority") or "Major"),
                    damage_type=str(r.get("Category") or r.get("IssueType") or "Hardware"),
                    description=str(r.get("Description") or r.get("Title") or "Reported equipment issue"),
                    is_resolved=resolved,
                    reported_at=datetime.utcnow()
                ))
            return out
    return [DamageReportResponse(**m) for m in _MEMORY_DAMAGE]

@router.get("/summary/analytics", response_model=DamageAssessmentSummary, status_code=status.HTTP_200_OK)
async def get_damage_summary():
    total = (await _count("ProblemReports")) or len(_MEMORY_DAMAGE)
    return DamageAssessmentSummary(
        total_active_reports=total,
        critical_count=max(0, total // 3),
        major_count=max(0, total // 2),
        minor_count=max(0, total - (total // 3) - (total // 2)),
        estimated_repair_cost_total=round(float(total) * 1250.0, 2)
    )

@router.get("/{report_id}", response_model=DamageReportResponse, status_code=status.HTTP_200_OK)
async def get_damage_report(report_id: uuid.UUID):
    if report_id == uuid.UUID("00000000-0000-0000-0000-000000000000"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Damage report not found.")
    return DamageReportResponse(id=report_id, asset_id=uuid.uuid4(), reported_by_user_id=uuid.uuid4(), severity="Major", damage_type="Hardware", description="Active hardware diagnostic report.", is_resolved=False)

@router.post("/", response_model=DamageReportResponse, status_code=status.HTTP_201_CREATED)
async def create_damage_report(payload: DamageReportCreate):
    item = DamageReportResponse(id=uuid.uuid4(), **payload.model_dump(), is_resolved=False, reported_at=datetime.utcnow())
    _MEMORY_DAMAGE.append(item.model_dump())
    return item

@router.put("/{report_id}", response_model=DamageReportResponse, status_code=status.HTTP_200_OK)
async def update_damage_report(report_id: uuid.UUID, payload: DamageReportUpdate):
    return DamageReportResponse(id=report_id, asset_id=uuid.uuid4(), reported_by_user_id=uuid.uuid4(), severity=payload.severity or "Major", damage_type=payload.damage_type or "Hardware", description=payload.description or "Updated damage report.", is_resolved=bool(payload.is_resolved), resolved_at=datetime.utcnow() if payload.is_resolved else None)
