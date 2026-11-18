from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import uuid
from app.schemas import BaseSchema

class ChatMessageSchema(BaseSchema):
    role: str = Field(..., description="Role of the sender")
    content: str = Field(..., description="Text content of the message")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatRequestSchema(BaseSchema):
    session_id: Optional[uuid.UUID] = Field(None)
    prompt: str = Field(..., min_length=1)
    context_asset_id: Optional[uuid.UUID] = Field(None)

class ChatResponseSchema(BaseSchema):
    session_id: uuid.UUID
    response: str
    tokens_used: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

class DiagnosticsAnalysisRequestSchema(BaseSchema):
    asset_id: uuid.UUID = Field(..., description="Target laboratory asset UUID")
    error_logs: List[str] = Field(..., description="Raw log strings or diagnostic dumps")
    telemetry_summary: Optional[Union[Dict[str, Any], str]] = Field(None, description="Optional telemetry snapshots or summary string")

class DiagnosticsAnalysisResponseSchema(BaseSchema):
    asset_id: uuid.UUID
    diagnosis: str
    recommended_actions: List[str]
    severity: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
