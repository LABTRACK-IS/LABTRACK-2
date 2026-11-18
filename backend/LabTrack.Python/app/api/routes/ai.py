from fastapi import APIRouter, HTTPException, Depends, status
from app.schemas.ai import ChatRequestSchema, ChatResponseSchema, DiagnosticsAnalysisRequestSchema, DiagnosticsAnalysisResponseSchema
from app.services.ai_service import AIService
from app.dependencies import get_ai_service

router = APIRouter()

@router.post("/chat", response_model=ChatResponseSchema, status_code=status.HTTP_200_OK)
async def handle_ai_chat(request: ChatRequestSchema, ai_service: AIService = Depends(get_ai_service)):
    return await ai_service.process_chat_message(request)

@router.post("/diagnose", response_model=DiagnosticsAnalysisResponseSchema, status_code=status.HTTP_200_OK)
async def analyze_diagnostics(request: DiagnosticsAnalysisRequestSchema, ai_service: AIService = Depends(get_ai_service)):
    if not request.error_logs:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Error logs list cannot be empty.")
    return await ai_service.analyze_diagnostics(request)
