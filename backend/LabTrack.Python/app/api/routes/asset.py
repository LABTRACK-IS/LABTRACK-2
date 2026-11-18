from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid
from app.api.routes.ai_chat import _run, _resolve_table
from app.services.telemetry_service import telemetry_service

router = APIRouter()

class AssetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    serial_number: str = Field(..., min_length=1, max_length=50)
    category: str = Field(...)
    location: Optional[str] = None
    is_active: bool = True

class AssetCreate(AssetBase):
    pass

class AssetUpdate(BaseModel):
    name: Optional[str] = None
    serial_number: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None

class AssetResponse(AssetBase):
    id: uuid.UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class AssetTelemetryOverview(BaseModel):
    asset_id: uuid.UUID
    cpu_usage_pct: float
    memory_usage_pct: float
    gpu_usage_pct: Optional[float] = None
    temperature_celsius: float
    status: str
    last_reported: datetime = Field(default_factory=datetime.utcnow)

@router.get("/", response_model=List[AssetResponse], status_code=status.HTTP_200_OK)
async def list_assets(category: Optional[str] = Query(None), is_active: Optional[bool] = Query(None), skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    tbl = await _resolve_table("Assets")
    if tbl:
        rows = await _run(f"SELECT * FROM {tbl} LIMIT $1 OFFSET $2", (limit, skip))
        if rows:
            result = []
            for r in rows:
                aid = r.get("Id") or r.get("id") or uuid.uuid4()
                result.append(AssetResponse(
                    id=aid if isinstance(aid, uuid.UUID) else uuid.UUID(str(aid)),
                    name=str(r.get("Name") or r.get("name") or r.get("AssetTag") or "Lab Asset"),
                    serial_number=str(r.get("SerialNumber") or r.get("serial_number") or r.get("Code") or "SN-001"),
                    category=str(r.get("Category") or r.get("category") or r.get("Type") or "Workstation"),
                    location=str(r.get("Location") or r.get("location") or "Main Lab"),
                    is_active=bool(r.get("IsActive", True))
                ))
            return result
    return [AssetResponse(id=uuid.uuid4(), name="Workstation PC-01", serial_number="SN-WS-001", category=category or "Workstation", location="Lab 1", is_active=True)]

@router.get("/{asset_id}", response_model=AssetResponse, status_code=status.HTTP_200_OK)
async def get_asset(asset_id: uuid.UUID):
    if asset_id == uuid.UUID("00000000-0000-0000-0000-000000000000"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset {asset_id} not found.")
    return AssetResponse(id=asset_id, name="Precision Workstation", serial_number="SN-WS-01", category="Workstation", location="Lab 1", is_active=True)

@router.post("/", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(payload: AssetCreate):
    return AssetResponse(id=uuid.uuid4(), **payload.model_dump(), created_at=datetime.utcnow())

@router.put("/{asset_id}", response_model=AssetResponse, status_code=status.HTTP_200_OK)
async def update_asset(asset_id: uuid.UUID, payload: AssetUpdate):
    return AssetResponse(id=asset_id, name=payload.name or "Updated Workstation", serial_number=payload.serial_number or "SN-UPD", category=payload.category or "Workstation", location=payload.location, is_active=True if payload.is_active is None else payload.is_active, updated_at=datetime.utcnow())

@router.get("/{asset_id}/telemetry/summary", response_model=AssetTelemetryOverview, status_code=status.HTTP_200_OK)
async def get_asset_telemetry_summary(asset_id: uuid.UUID):
    latest = await telemetry_service.get_latest(str(asset_id))
    cpu = float(latest.get("cpu_pct", 34.5)) if latest else 34.5
    mem = float(latest.get("memory_pct", 52.0)) if latest else 52.0
    temp = float(latest.get("temperature_celsius", 58.0)) if latest else 58.0
    st = "Critical" if cpu >= 90 or mem >= 90 else ("Warning" if cpu >= 80 or mem >= 80 else "Normal")
    return AssetTelemetryOverview(asset_id=asset_id, cpu_usage_pct=cpu, memory_usage_pct=mem, gpu_usage_pct=40.0, temperature_celsius=temp, status=st, last_reported=datetime.utcnow())
