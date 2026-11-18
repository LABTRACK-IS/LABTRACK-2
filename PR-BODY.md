## Purpose

Second iteration (v2) of LabTrack from `C:\360TSDownloads\labtrack 2`.

## Change summary

| Area | Added | Removed | Modified |
|------|-------|---------|----------|
| Backend | 14 | 6 | 26 |
| Frontend | 2 | 4 | 45 |

Detailed diff: [CHANGELOG.md](./CHANGELOG.md)

## Backend top changes

- `backend/labtrack.python/app/api/routes/ai_chat.py` — **+608 / -1024**
- `backend/labtrack.csharp/src/labtrack.api/controllers/authcontroller.cs` — **+2 / -301**
- `backend/labtrack.csharp/src/labtrack.api/program.cs` — **+14 / -213**
- `backend/labtrack.csharp/src/labtrack.api/services/problemreportservice.cs` — **+90 / -135**
- `backend/labtrack.csharp/src/labtrack.api/controllers/aiassistantcontroller.cs` — **+41 / -120**
- `backend/labtrack.csharp/src/labtrack.api/controllers/problemreportcontroller.cs` — **+93 / -41**
- `backend/labtrack.python/app/db/vector_db.py` — **+22 / -75**
- `backend/labtrack.python/app/services/telemetry_service.py` — **+22 / -75**
- `backend/labtrack.python/app/api/routes/asset.py` — **+24 / -63**
- `backend/labtrack.python/app/clients/llm_client.py` — **+31 / -46**

## Frontend top changes

- `frontend/src/components/admin/maintenanceview.tsx` — **+408 / -3163**
- `frontend/src/components/admin/analyticsreportsview.tsx` — **+455 / -2449**
- `frontend/src/components/admin/useraccessmanagementview.tsx` — **+550 / -1820**
- `frontend/src/components/admin/issueservicedeskview.tsx` — **+433 / -1838**
- `frontend/src/components/instructor/notificationsview.tsx` — **+424 / -1844**
- `frontend/src/components/instructor/labavailabilityview.tsx` — **+535 / -1581**
- `frontend/src/components/instructor/studentsessionsview.tsx` — **+351 / -1651**
- `frontend/src/components/instructor/overviewview.tsx` — **+543 / -1290**
- `frontend/src/components/instructor/reservationsview.tsx` — **+446 / -1371**
- `frontend/src/components/admin/inventorytransferview.tsx` — **+417 / -1365**

## QA checklist

- [ ] dotnet build OK
- [ ] tsc --noEmit = 0 errors
- [ ] /health/live = 200
- [ ] Swagger lists all controllers
- [ ] EF migrations apply
- [ ] No bin/obj/node_modules/.env tracked

🤖 Generated: 2026-11-18 08:22:57
