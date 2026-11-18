## Purpose

Second iteration (v2) of LabTrack, imported from `C:\360TSDownloads\labtrack 2`.

This PR replaces the v1 baseline snapshot with the refined build. Focus: **stability, structural cleanup, and verified build/type health** — not feature showcase.

---

## Backend — what changed

- **Project file cleanup:** removed `<Compile Include>` directives in `.csproj` / `Directory.Build.props` that caused `CS0101` duplicate-definition errors in the v1 push.
- **Current state:** 459 C# files (~34792 lines), 29 controllers registered.
- **Controllers:** AiAssistant, Analytics, Asset, Audit, Auth, ChainOfCustody, Communication, Financial, IdempotencyRecords, InstructorCommunication, Laboratories, Maintenance, MaintenanceRecord, MaintenanceRecords, Network, NetworkIncident, NetworkInfo, Notification, PcUsage, ProblemReport, Qr, QrAdmin, QrSession, RepairTicket, Replacement, ReplacementRecord, Reservation, Users, Workstations

**Files modified vs v1:** 32

---

## Frontend — what changed

- **Current state:** 73 TS/TSX files (~26669 lines).
- TypeScript check: **clean** (no `error TS` lines).
- Router and page structure stable; no breaking API integration changes in this pass.

**Files added vs v1:** 2

**Files modified vs v1:** 48

**Files removed vs v1:** 4

---

## Build & test status

| Check | Result |
|---|---|
| `dotnet build` | ✅ Build succeeded |
| `npx tsc --noEmit` | ✅ 0 errors |
| `gh auth setup-git` | ✅ configured |

---

## QA focus areas (different from v1 review)

Unlike v1, this PR should be reviewed for **regressions and cleanup**, not just features:

- [ ] No duplicate `.cs` definitions after `.csproj` cleanup (verify `CS0101` gone in CI)
- [ ] EF Core migrations still apply cleanly
- [ ] ``/swagger/v1/swagger.json`` lists exactly the expected controllers (no doubles)
- [ ] Frontend build output identical structure to v1 (or intentional delta documented)
- [ ] ``git ls-files`` shows no ``bin/``, ``obj/``, ``node_modules/``, or backup folders
- [ ] Health checks still green: ``/health/live`` = 200
- [ ] Diff vs v1 is intentional — reject if unrelated churn appears

---

## How to verify

```bash
# Backend
cd backend/LabTrack.CSharp/src/LabTrack.Api
dotnet build && dotnet run

# Frontend (new terminal)
cd frontend && npm install && npm run dev

# Compare against v1 (if you have the old commit)
git diff <v1-commit>..HEAD -- backend/ frontend/ --stat
```

---

🤖 Auto-generated v2 description on 2026-11-18 08:03:49
