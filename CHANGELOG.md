# CHANGELOG - v2 vs v1

Auto-generated. **v1** (`C:\labtrack`) → **v2** (`C:\360TSDownloads\labtrack 2`).

Generated: 2026-11-18 08:22:57

## Summary

| Area | Added | Removed | Modified |
|------|-------|---------|----------|
| Backend | 14 | 6 | 26 |
| Frontend | 2 | 4 | 45 |

---

## Backend

### Added (14)

- `backend/labtrack.python/app/middleware/tracing.py` **[Python]** — 41 lines
- `backend/labtrack.python/app/middleware/logging.py` **[Python]** — 38 lines
- `backend/labtrack.python/app/middleware/correlation.py` **[Python]** — 22 lines
- `backend/labtrack.python/app/api/routes/ai.py` **[Python]** — 13 lines
- `backend/labtrack.python/app/middleware/__init__.py` **[Python]** — 8 lines
- `backend/labtrack.python/app/exceptions/__init__.py` **[Python]** — 81 lines
- `backend/labtrack.python/app/services/context_service.py` **[Service]** — 72 lines
- `backend/labtrack.python/app/middleware/logging_middleware.py` **[Python]** — 37 lines
- `backend/labtrack.python/app/security/request_validation.py` **[Python]** — 63 lines
- `backend/labtrack.python/app/logging/__init__.py` **[Python]** — 49 lines
- `backend/labtrack.python/app/exceptions/custom.py` **[Python]** — 46 lines
- `backend/labtrack.python/app/dependencies.py` **[Python]** — 94 lines
- `backend/labtrack.python/test_pgvector.py` **[Python]** — 5 lines
- `backend/labtrack.python/app/logging/logging_config.py` **[Python]** — 33 lines

### Removed (6)

- `backend/labtrack.python/pyrightconfig.json` **[Config]**
- `backend/labtrack.python/app/exceptions.py` **[Python]**
- `backend/labtrack.python/app/db/postgres.py` **[Python]**
- `backend/labtrack.python/app/middleware.py` **[Python]**
- `backend/.vscode/settings.json` **[Config]**
- `backend/labtrack.python/.vscode/settings.json` **[Config]**

### Modified (26)

####  (26)

| File | +/- | Key |
|------|-----|-----|
| `backend/labtrack.python/app/api/routes/ai_chat.py` | +608 / -1024 | LabTrack AI Engine v10 - Gemini 2.5 Pro + Full-Database Live Intelligence · - Unified ADMIN / TEC... |
| `backend/labtrack.csharp/src/labtrack.api/controllers/authcontroller.cs` | +2 / -301 | public AuthController(IAuthService authService, ILogger<AuthController> logger) · [HttpPost("regi... |
| `backend/labtrack.csharp/src/labtrack.api/program.cs` | +14 / -213 | // API layer services (implement interfaces declared in Controllers) · ?? "http://localhost:8000"; |
| `backend/labtrack.csharp/src/labtrack.api/services/problemreportservice.cs` | +90 / -135 | private Guid GetUserIdOrThrow() · if (!Guid.TryParse(claim, out var userId) \|\| userId == Guid.E... |
| `backend/labtrack.csharp/src/labtrack.api/controllers/aiassistantcontroller.cs` | +41 / -120 | // // [ApiController] · [FromBody] AiChatRequestDto request, |
| `backend/labtrack.csharp/src/labtrack.api/controllers/problemreportcontroller.cs` | +93 / -41 | DateTime? ResolvedAt · string? Priority |
| `backend/labtrack.python/app/db/vector_db.py` | +22 / -75 | _vector_engine = create_async_engine( · settings.database_url, |
| `backend/labtrack.python/app/services/telemetry_service.py` | +22 / -75 | """Stores and aggregates PC telemetry received from workstation agents.""" · # In-memory store ke... |
| `backend/labtrack.python/app/api/routes/asset.py` | +24 / -63 | from typing import List, Optional · from app.api.routes.ai_chat import _run, _resolve_table |
| `backend/labtrack.python/app/clients/llm_client.py` | +31 / -46 | temperature: float = Field(0.2, ge=0.0, le=2.0) · model: str = Field("gemini-2.5-pro", descriptio... |
| `backend/labtrack.python/app/schemas/__init__.py` | +34 / -9 | LabTrack Pydantic Schemas Package Initialization. · Exports core data transfer objects (DTOs) and... |
| `backend/labtrack.python/app/security/__init__.py` | +29 / -14 | import logging · logger = logging.getLogger(__name__) |
| `backend/labtrack.python/app/clients/csharp_api.py` | +4 / -30 | """HTTP client wrapper for the LabTrack C# backend.""" · self.base_url = base_url.rstrip("/") |
| `backend/labtrack.python/app/api/routes/damage.py` | +12 / -22 | from typing import List, Optional · from app.api.routes.ai_chat import _run, _resolve_table, _count |
| `backend/labtrack.python/app/schemas/ai.py` | +9 / -9 | from pydantic import BaseModel, Field · role: str = Field(..., description="Role of the sender") |
| `backend/labtrack.python/app/security/internal_auth.py` | +8 / -5 | import logging · logger = logging.getLogger("LabTrack.Python.Security") |
| `backend/labtrack.csharp/src/labtrack.api/properties/launchsettings.json` | +1 / -11 | {"profiles":{"http":{"commandName":"Project","applicationUrl":"http://0.0.0.0:5001","environmentV... |
| `backend/labtrack.csharp/src/labtrack.api/appsettings.json` | +1 / -10 | } |
| `backend/labtrack.python/app/clients/__init__.py` | +9 / -2 | LabTrack External Service Clients Package Initialization. · Contains asynchronous API client abst... |
| `backend/labtrack.csharp/src/labtrack.api/controllers/pcusagecontroller.cs` | +5 / -5 | if (request.SessionId == Guid.Empty \|\| string.IsNullOrWhiteSpace(request.QrToken)) · // AUTO-AS... |
| `backend/labtrack.python/app/db/__init__.py` | +2 / -5 | """LabTrack Database & Vector Store Package.""" · __all__ = ["init_vector_db", "ensure_vector_ext... |
| `backend/labtrack.csharp/src/labtrack.api/models/pcusagemodels.cs` | +4 / -1 | public sealed record HeartbeatRequestDto( · string QrToken |
| `backend/labtrack.python/app/main.py` | +2 / -3 | from app.middleware.correlation import CorrelationIdMiddleware · from app.middleware.logging impo... |
| `backend/labtrack.python/app/services/__init__.py` | +2 / -2 | from app.services.context_service import ContextService · "AIService", "AssetService", "Classific... |
| `backend/labtrack.csharp/src/labtrack.api/globalusings.cs` | +0 / -1 | (minor) |
| `backend/labtrack.csharp/src/labtrack.api/services/pythonaiservice.cs` | +0 / -1 | (minor) |

---

## Frontend

### Added (2)

- `frontend/src/components/common/labtrackaichatbot.tsx` **[Component]** — 133 lines
- `frontend/src/new-feature.ts` **[Other]** — 1 lines

### Removed (4)

- `frontend/src/components/common/sequentialtypewriterbanner.tsx` **[Component]**
- `frontend/src/api/services.ts` **[Other]**
- `frontend/src/components/common/airichmessagerenderer.tsx` **[Component]**
- `frontend/src/components/portal/youtubenotificationbell.tsx` **[Component]**

### Modified (45)

####  (45)

| File | +/- | Key |
|------|-----|-----|
| `frontend/src/components/admin/maintenanceview.tsx` | +408 / -3163 | import React, { useState, useMemo, useEffect } from 'react'; · import { |
| `frontend/src/components/admin/analyticsreportsview.tsx` | +455 / -2449 | import { · BarChart3, FileSpreadsheet, FileText, Clock, |
| `frontend/src/components/admin/useraccessmanagementview.tsx` | +550 / -1820 | import React, { useEffect, useState } from 'react'; · import { |
| `frontend/src/components/admin/issueservicedeskview.tsx` | +433 / -1838 | import React, { useEffect,  useState, useMemo } from 'react'; · import { |
| `frontend/src/components/instructor/notificationsview.tsx` | +424 / -1844 | import React, { useState, useMemo, useEffect, useCallback } from 'react'; · import { |
| `frontend/src/components/instructor/labavailabilityview.tsx` | +535 / -1581 | import React, { useState, useMemo, useEffect } from 'react'; · import { |
| `frontend/src/components/instructor/studentsessionsview.tsx` | +351 / -1651 | import React, { useState, useEffect, useMemo } from 'react'; · Download, Filter, CheckCircle2, Sp... |
| `frontend/src/components/instructor/overviewview.tsx` | +543 / -1290 | import React, { useState, useMemo, useEffect } from 'react'; · import { |
| `frontend/src/components/instructor/reservationsview.tsx` | +446 / -1371 | import React, { useEffect,  useState, useMemo } from 'react'; · import { |
| `frontend/src/components/admin/inventorytransferview.tsx` | +417 / -1365 | import React, { useEffect,  useState, useMemo } from 'react'; · import { |
| `frontend/src/components/admin/overviewview.tsx` | +481 / -1190 | import { · Tv, CheckCircle, AlertTriangle, Radio, Thermometer, BatteryCharging, |
| `frontend/src/components/instructor/usageanalyticsview.tsx` | +432 / -1175 | import { · BarChart3, Calendar, Download, RefreshCw, Edit3, |
| `frontend/src/components/instructor/reportproblemview.tsx` | +327 / -1212 | import { · AlertTriangle, CheckCircle2, Clock, Wrench, Trash2, |
| `frontend/src/components/instructor/profileview.tsx` | +364 / -1169 | import React, { useEffect,  useState, useRef } from 'react'; · import { |
| `frontend/src/components/admin/auditlogsview.tsx` | +389 / -1134 | import { · FileText, Search, Plus, Trash2, Edit3, Shield, Download, Check, Copy, |
| `frontend/src/components/admin/notificationsmanagementview.tsx` | +254 / -1162 | import React, { useState, useEffect, useCallback, useMemo } from 'react'; · import { |
| `frontend/src/components/admin/qrmanagementview.tsx` | +329 / -1013 | import React, { useState, useEffect } from 'react'; · import { |
| `frontend/src/components/admin/profilesettingsview.tsx` | +261 / -997 | import React, { useState, useEffect } from 'react'; · import { |
| `frontend/src/components/admin/campuseslabsview.tsx` | +318 / -781 | import { · Building, Globe, Layers, Thermometer, Zap, Search, X, |
| `frontend/src/components/instructor/aiassistantview.tsx` | +241 / -857 | import React, { useState, useRef, useEffect } from 'react'; · import { |
| `frontend/src/components/admin/aiassistantview.tsx` | +280 / -787 | import React, { useState, useEffect, useRef } from 'react'; · import { |
| `frontend/src/pages/auth/forgot-password-page.tsx` | +82 / -496 | import React, { useState } from 'react'; · import { Link, useParams } from "react-router-dom"; |
| `frontend/src/pages/landing/homepage.tsx` | +112 / -461 | import React, { useState, useEffect } from 'react'; · Wrench, Sparkles, Building2, Cpu, FileText, |
| `frontend/src/components/portal/portalshell.tsx` | +111 / -311 | import AdminNotificationsView from '../admin/AdminNotificationsView'; · import React, { useState,... |
| `frontend/src/lib/api-client.ts` | +52 / -248 | const BASE_URL = import.meta.env.VITE_API_BASE_URL \|\| ''; · baseURL: BASE_URL, |
| `frontend/src/components/auth/authlayout.tsx` | +8 / -254 | import { Monitor, ShieldCheck } from "lucide-react"; · {/* LEFT SIDE (Branding) */} |
| `frontend/src/pages/landing/aboutpage.tsx` | +27 / -227 | Server, CheckCircle2, Lock, Laptop, Zap, ArrowRight, · UserCheck, Database, RefreshCw, FileText, ... |
| `frontend/src/layouts/landinglayout.tsx` | +47 / -203 | import React, { useState, createContext, useContext } from 'react'; · <div className={`min-h-scre... |
| `frontend/src/lib/data-adapters.ts` | +55 / -140 | import { apiClient } from './api-client'; · // Map Admin & Instructor Endpoint Calls |
| `frontend/src/components/common/globalaichatbot.tsx` | +62 / -114 | import { X, Send, Sparkles } from "lucide-react"; · import apiClient from "@/lib/api-client"; |
| `frontend/src/api/client.ts` | +57 / -59 | import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'; · import { AuthResponse } ... |
| `frontend/src/lib/signalr.ts` | +60 / -26 | const AUTH_TOKEN_KEY = 'jrmsu_labtrack_auth_token'; · * SignalR Hub Endpoints Configuration |
| `frontend/src/hooks/userealtime.ts` | +19 / -47 | const BASE_URL = import.meta.env.VITE_API_BASE_URL \|\| 'http://localhost:5000'; · const token = ... |
| `frontend/src/api/apiclient.ts` | +2 / -60 | import { apiClient } from '../lib/api-client'; · export { apiClient }; |
| `frontend/src/lib/axios.ts` | +58 / -2 | import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse, AxiosError } from 'axio... |
| `frontend/src/assets/styles/fonts.css` | +38 / -4 | @font-face { · font-family: 'Inter'; |
| `frontend/src/components/admin/qrgeneratormodal.tsx` | +5 / -30 | import React, { useState } from 'react'; · import { X, Printer, QrCode, Sparkles } from 'lucide-r... |
| `frontend/src/config/env.ts` | +4 / -24 | return import.meta.env[key] \|\| defaultValue; · apiBaseUrl: getEnvVar('VITE_API_BASE_URL', typeo... |
| `frontend/vite.config.ts` | +8 / -20 | import os from 'os'; · if (net.family === 'IPv4' && !net.internal) return net.address; |
| `frontend/tailwind.config.ts` | +0 / -8 | (minor) |
| `frontend/src/components/portal/headernotificationbell.tsx` | +3 / -4 | message: 'High thermal sensor alert reaching 78°C on PC-202.', · await api.post('/api/v1/notifica... |
| `frontend/index.html` | +4 / -3 | content="JRMSU LabTrack Ã¢â‚¬â€ Jose Rizal Memorial State University Computer Laboratory Managem... |
| `frontend/src/pages/auth/register-page.tsx` | +3 / -1 | <Link to="/" className="fixed top-6 left-6 p-3 bg-slate-900/50 hover:bg-slate-900/80 backdrop-blu... |
| `frontend/src/pages/student/student-portal-page.tsx` | +2 / -2 | className="fixed inset-0 z-0 bg-cover bg-center bg-no-repeat" · <div className="fixed inset-0 z-0... |
| `frontend/src/pages/auth/login-page.tsx` | +3 / -1 | <Link to="/" className="fixed top-6 left-6 p-3 bg-slate-900/50 hover:bg-slate-900/80 backdrop-blu... |

---

## Cleanup

- Removed `.bak`, `.bak2`, `cleanup-*.txt` from git + disk
- Updated `.gitignore`

🤖 Auto-generated
