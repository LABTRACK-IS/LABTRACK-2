"""
LabTrack AI Engine v10 - Gemini 2.5 Pro + Full-Database Live Intelligence
- Unified ADMIN / TECHNICIAN (Sole Admin) Role
- Live PostgreSQL Multi-Table Snapshot & Deep Query Reasoning
- Bilingual (English, Tagalog, Taglish) Conversational Copilot
- Strict Word-Boundary Intent Classification (No Substring Collisions)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
import time, uuid, json, logging, re, os, difflib, httpx

logger = logging.getLogger("LabTrack.Python.AIChat")
router = APIRouter()

try:
    import asyncpg
    _ASYNCPG = True
except ImportError:
    _ASYNCPG = False

try:
    from app.config import settings
    _HAS_SETTINGS = True
except Exception:
    _HAS_SETTINGS = False

try:
    from groq import Groq
    _GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    _groq_client = Groq(api_key=_GROQ_API_KEY) if _GROQ_API_KEY else None
    _HAS_GROQ = _groq_client is not None
except ImportError:
    _HAS_GROQ = False
    _groq_client = None


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    system_context: Optional[str] = None
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    response: str
    processing_time_ms: float = 0.0
    tokens_used: int = 0
    created_at: str
    suggestions: List[str] = []
    actions: List[Dict[str, Any]] = []

class PredictiveMaintenanceRequest(BaseModel):
    asset_id: str
    system_usage_hours: int = 0

class PredictiveMaintenanceResponse(BaseModel):
    asset_id: str
    failure_risk_percentage: float
    recommendation: str
    next_maintenance_due: str

class RepairCostRequest(BaseModel):
    problem_report_id: str
    issue_description: str = ""
    hardware_model: str = ""

class RepairCostResponse(BaseModel):
    problem_report_id: str
    estimated_cost: float
    currency: str
    labor_complexity: str

class DiagnoseRequest(BaseModel):
    asset_id: Optional[str] = None
    error_logs: List[str] = []
    telemetry_summary: Optional[Dict[str, Any]] = None

class DiagnoseResponse(BaseModel):
    asset_id: Optional[str] = None
    diagnosis: str
    recommended_actions: List[str]
    severity: str
    confidence_score: float
    analyzed_at: str


def _db_dsn() -> str:
    env = os.getenv("DATABASE_URL")
    if env and env.startswith("postgres"):
        return env.replace("+asyncpg", "")
    if _HAS_SETTINGS:
        host = getattr(settings, "DB_HOST", "localhost") or "localhost"
        port = getattr(settings, "DB_PORT", 5432) or 5432
        user = getattr(settings, "DB_USER", "postgres") or "postgres"
        pwd = getattr(settings, "DB_PASSWORD", "sven292005") or "sven292005"
        db = getattr(settings, "DB_NAME", "labtrack_db") or "labtrack_db"
        return f"postgresql://{user}:{pwd}@{host}:{port}/{db}"
    return "postgresql://postgres:sven292005@localhost:5432/labtrack_db"


async def _run(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    if not _ASYNCPG:
        return []
    try:
        conn = await asyncpg.connect(_db_dsn(), timeout=4)
        try:
            rows = await conn.fetch(sql, *params)
            return [dict(r) for r in rows]
        finally:
            await conn.close()
    except Exception as e:
        logger.debug(f"DB query note: {e}")
        return []


async def _resolve_table(table: str) -> Optional[str]:
    rows = await _run(
        "SELECT table_schema, table_name FROM information_schema.tables "
        "WHERE table_schema IN ('labtrack_schema', 'public') AND LOWER(table_name) = LOWER($1) LIMIT 1",
        (table,)
    )
    if rows:
        return f'{rows[0]["table_schema"]}."{rows[0]["table_name"]}"'
    return None


async def _count(table: str, where: Optional[str] = None, params: tuple = ()) -> Optional[int]:
    full_tbl = await _resolve_table(table)
    if not full_tbl:
        return None
    sql = f"SELECT COUNT(*) AS c FROM {full_tbl}"
    if where:
        sql += f" WHERE {where}"
    rows = await _run(sql, params)
    if rows and rows[0].get("c") is not None:
        return int(rows[0]["c"])
    return None


async def _columns(table: str) -> List[Dict[str, str]]:
    rows = await _run(
        "SELECT table_schema, table_name FROM information_schema.tables "
        "WHERE table_schema IN ('labtrack_schema', 'public') AND LOWER(table_name) = LOWER($1) LIMIT 1",
        (table,)
    )
    if not rows:
        return []
    return await _run(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = $1 AND table_name = $2",
        (rows[0]["table_schema"], rows[0]["table_name"])
    )


def _pick_money_col(cols: List[Dict[str, str]]) -> Optional[str]:
    num = {"numeric", "decimal", "double precision", "real", "integer", "bigint", "smallint"}
    cands = [c for c in cols if c["data_type"] in num and "id" not in c["column_name"].lower()]
    if not cands:
        return None
    for pref in ("amount", "cost", "total", "price", "value", "expense", "budget"):
        for c in cands:
            if pref in c["column_name"].lower():
                return c["column_name"]
    return cands[0]["column_name"]


async def _sum_money(table: str = "FinancialTransactions") -> Tuple[float, int, str]:
    grand_total = 0.0
    total_records = 0
    matched_col = "Cost"
    for candidate in ("FinancialTransactions", "FinancialExpenses", "ReplacementRecords", "MaintenanceRecords", "RepairTickets", "Assets"):
        full_tbl = await _resolve_table(candidate)
        if not full_tbl:
            continue
        cols = await _columns(candidate)
        col = _pick_money_col(cols)
        if not col:
            continue
        rows = await _run(f'SELECT COALESCE(SUM("{col}"), 0) AS s, COUNT(*) AS c FROM {full_tbl}')
        if rows and int(rows[0]["c"]) > 0:
            val = float(rows[0]["s"] or 0.0)
            cnt = int(rows[0]["c"] or 0)
            if val > 0 or total_records == 0:
                grand_total += val
                total_records += cnt
                matched_col = col
    return (grand_total, total_records, matched_col)


async def _get_live_system_snapshot() -> Dict[str, Any]:
    """Builds a real-time comprehensive telemetry & database snapshot of the entire LabTrack system."""
    snap: Dict[str, Any] = {
        "total_users": await _count("Users") or 0,
        "admin_tech_users": await _count("Users", "UPPER(CAST(\"Role\" AS TEXT)) IN ('TECHNICIAN', 'ADMIN', 'SUPERADMIN')") or 0,
        "instructor_users": await _count("Users", "UPPER(CAST(\"Role\" AS TEXT)) = 'INSTRUCTOR'") or 0,
        "student_users": await _count("Users", "UPPER(CAST(\"Role\" AS TEXT)) = 'STUDENT'") or 0,
        "total_labs": await _count("Laboratories") or 0,
        "total_workstations": await _count("Workstations") or 0,
        "total_assets": await _count("Assets") or 0,
        "broken_assets": 0,
        "active_sessions": 0,
        "total_sessions": await _count("PcUsageLogs") or 0,
        "pending_reports": 0,
        "total_reports": await _count("ProblemReports") or 0,
        "open_repairs": 0,
        "total_repairs": await _count("RepairTickets") or 0,
        "total_reservations": await _count("Reservations") or 0,
        "total_audit_logs": await _count("AuditLogs") or 0,
        "financial_total": 0.0,
        "financial_records": 0,
        "sample_labs": [],
        "sample_assets": [],
        "sample_users": [],
    }

    full_assets = await _resolve_table("Assets")
    if full_assets:
        for cond in ("UPPER(CAST(\"Status\" AS TEXT)) IN ('OUT_OF_ORDER','BROKEN','MAINTENANCE','FAULTY','INACTIVE','DAMAGED')", '"IsActive" = false'):
            r = await _run(f"SELECT COUNT(*) AS c FROM {full_assets} WHERE {cond}")
            if r and r[0].get("c") is not None:
                snap["broken_assets"] = int(r[0]["c"])
                break
        asset_rows = await _run(f"SELECT * FROM {full_assets} LIMIT 5")
        for ar in asset_rows:
            nm = ar.get("Name") or ar.get("AssetTag") or ar.get("Code") or "Asset"
            st = ar.get("Status") or ("Active" if ar.get("IsActive", True) else "Inactive")
            snap["sample_assets"].append(f"{nm} ({st})")

    full_labs = await _resolve_table("Laboratories")
    if full_labs:
        lab_rows = await _run(f"SELECT * FROM {full_labs} LIMIT 5")
        for lr in lab_rows:
            ln = lr.get("Name") or lr.get("Code") or "Lab"
            snap["sample_labs"].append(str(ln))

    full_users = await _resolve_table("Users")
    if full_users:
        u_rows = await _run(f"SELECT * FROM {full_users} LIMIT 5")
        for ur in u_rows:
            fn = ur.get("FullName") or f"{ur.get('FirstName','')} {ur.get('LastName','')}".strip() or ur.get("Email") or "User"
            rl = ur.get("Role") or "USER"
            snap["sample_users"].append(f"{fn} [{rl}]")

    full_pc = await _resolve_table("PcUsageLogs")
    if full_pc:
        for col in ("EndedAtUtc", "LogoutTimeUtc", "SessionEndUtc", "EndTimeUtc"):
            r = await _run(f'SELECT COUNT(*) AS c FROM {full_pc} WHERE "{col}" IS NULL')
            if r and r[0].get("c") is not None:
                snap["active_sessions"] = int(r[0]["c"])
                break

    full_pr = await _resolve_table("ProblemReports")
    if full_pr:
        for cond in ("UPPER(CAST(\"Status\" AS TEXT)) NOT IN ('RESOLVED','CLOSED','COMPLETED','CANCELLED')", '"IsResolved" = false'):
            r = await _run(f"SELECT COUNT(*) AS c FROM {full_pr} WHERE {cond}")
            if r and r[0].get("c") is not None:
                snap["pending_reports"] = int(r[0]["c"])
                break

    full_rt = await _resolve_table("RepairTickets")
    if full_rt:
        for cond in ("UPPER(CAST(\"Status\" AS TEXT)) NOT IN ('RESOLVED','CLOSED','COMPLETED','CANCELLED')", '"ResolvedAtUtc" IS NULL'):
            r = await _run(f"SELECT COUNT(*) AS c FROM {full_rt} WHERE {cond}")
            if r and r[0].get("c") is not None:
                snap["open_repairs"] = int(r[0]["c"])
                break

    fin_sum, fin_cnt, _ = await _sum_money()
    snap["financial_total"] = fin_sum
    snap["financial_records"] = fin_cnt
    return snap


SYSTEM_MAP = {
    "ADMIN": {
        "overview": {"label": "Overview", "path": "/admin/overview"},
        "assets": {"label": "Assets & Workstations", "path": "/admin/assets"},
        "maintenance": {"label": "Maintenance", "path": "/admin/maintenance"},
        "issues": {"label": "Issue Service Desk", "path": "/admin/issues"},
        "inventory": {"label": "Inventory Transfer", "path": "/admin/inventory"},
        "reservations": {"label": "Reservations", "path": "/admin/reservations"},
        "sessions": {"label": "Sessions", "path": "/admin/sessions"},
        "users": {"label": "User Access", "path": "/admin/users"},
        "campuses": {"label": "Campuses & Labs", "path": "/admin/campuses"},
        "qr": {"label": "QR Management", "path": "/admin/qr"},
        "analytics": {"label": "Analytics & Reports", "path": "/admin/analytics"},
        "financial": {"label": "Financial Reports", "path": "/admin/financial"},
        "audit": {"label": "Audit Logs", "path": "/admin/audit"},
        "notifications": {"label": "Notifications", "path": "/admin/notifications"},
        "ai": {"label": "AI Assistant", "path": "/admin/ai"},
        "profile": {"label": "Profile", "path": "/admin/profile"},
    },
    "INSTRUCTOR": {
        "overview": {"label": "Overview", "path": "/instructor/overview"},
        "lab_availability": {"label": "Lab Availability", "path": "/instructor/lab_availability"},
        "reservations": {"label": "Reservations", "path": "/instructor/reservations"},
        "requests": {"label": "My Requests", "path": "/instructor/requests"},
        "notifications": {"label": "Notifications", "path": "/instructor/notifications"},
        "report_problem": {"label": "Report Problem", "path": "/instructor/report_problem"},
        "analytics": {"label": "Usage Analytics", "path": "/instructor/analytics"},
        "ai": {"label": "AI Assistant", "path": "/instructor/ai"},
        "profile": {"label": "Profile", "path": "/instructor/profile"},
    },
    "STUDENT": {
        "home": {"label": "Home", "path": "/student"},
        "history": {"label": "History", "path": "/student/history"},
        "notifications": {"label": "Notifications", "path": "/student/notifications"},
        "profile": {"label": "Profile", "path": "/student/profile"},
    },
    "GUEST": {
        "home": {"label": "Home", "path": "/"},
        "laboratories": {"label": "Laboratories", "path": "/laboratories"},
        "features": {"label": "Features", "path": "/features"},
        "about": {"label": "About", "path": "/about"},
        "login": {"label": "Login", "path": "/login/admin"},
        "register": {"label": "Register", "path": "/register/admin"},
    },
}
SYSTEM_MAP["TECHNICIAN"] = SYSTEM_MAP["ADMIN"]


KB = {
    "assets": {
        "kw": ["add asset", "new asset", "register workstation", "register asset", "paano mag add ng asset", "paano magdagdag ng pc"],
        "responses": {
            "ADMIN": "To add or manage assets and workstations, open Assets & Workstations (/admin/assets) from the sidebar and click Add Asset. Enter the asset tag, serial number, category, campus, and laboratory. Upon saving, LabTrack automatically generates its unique QR code and links it to live telemetry.",
            "INSTRUCTOR": "Instructors can view live workstation status under Lab Availability (/instructor/lab_availability). Only Admin/Technicians can register or modify hardware assets.",
            "STUDENT": "Your workstation has a unique QR code and asset tag shown on your Home screen. If the hardware has an issue, tap Report a Problem.",
        },
    },
    "maintenance": {
        "kw": ["schedule maintenance", "how to repair", "create repair ticket", "assign technician", "paano mag report ng sira"],
        "responses": {
            "ADMIN": "As Admin/Technician, open Maintenance (/admin/maintenance) or Issue Service Desk (/admin/issues) to review reported problems, create or update repair tickets, log replacement parts, and track preventive maintenance schedules.",
            "INSTRUCTOR": "If a PC fails during your class, go to Report Problem (/instructor/report_problem), select the workstation, and submit the issue. You can monitor repair progress in My Requests.",
            "STUDENT": "Tap Report a Problem on your Home screen, select the issue category (e.g., No Display, Peripherals, Network), and submit so the Admin/Technician is alerted immediately.",
        },
    },
    "reservation": {
        "kw": ["how to book", "book a lab", "new reservation", "approve reservation", "paano mag book ng lab", "paano mag reserve"],
        "responses": {
            "ADMIN": "Open Reservations (/admin/reservations) to review pending laboratory booking requests from instructors. The system highlights any schedule conflicts automatically before you click Approve or Reject.",
            "INSTRUCTOR": "Open Reservations (/instructor/reservations) and click New Reservation. Choose the campus, laboratory, date, time slot, and class purpose, then submit for Admin/Technician approval.",
            "STUDENT": "Instructors book laboratory schedules for classes. When you arrive at the lab, simply scan the QR code on your assigned workstation to start your session.",
        },
    },
    "qr": {
        "kw": ["generate qr", "print qr", "scan qr", "how does qr work", "paano gamitin ang qr", "qr code"],
        "responses": {
            "ADMIN": "Open QR Management (/admin/qr) to generate, download, print, or rotate cryptographic QR tokens for any laboratory workstation.",
            "INSTRUCTOR": "Students scan the workstation QR code upon arrival to start their tracked PC session. If a QR sticker is damaged, report it via Report Problem.",
            "STUDENT": "Point your phone camera at the QR code on your workstation and tap the link to automatically start your PC usage session without needing a password.",
        },
    },
    "rules": {
        "kw": ["lab rules", "lab guidelines", "policies", "allowed in the lab", "patakaran sa lab", "bawal sa lab"],
        "responses": {
            "ADMIN": "LabTrack enforces 5 core rules: (1) Scan workstation QR upon arrival, (2) Strictly no food or drinks inside the lab, (3) Report hardware faults immediately, (4) Idle sessions auto-close after 59 seconds without a heartbeat, and (5) Keep workstations clean.",
            "INSTRUCTOR": "Remind students to scan their workstation QR code on arrival, avoid food/drinks, report hardware issues immediately, and log out after class.",
            "STUDENT": "Lab rules: Always scan the QR code when you sit down, no food or drinks inside the lab, report any PC issue immediately, and log out when finished (sessions auto-close after 59s of inactivity).",
        },
    },
}


def _norm_role(r: Any) -> str:
    if not r:
        return "ADMIN"
    r = str(r).upper().strip()
    if r in ("TECHNICIAN", "ADMIN", "SUPERADMIN", "TECH"):
        return "ADMIN"
    return r if r in ("ADMIN", "INSTRUCTOR", "STUDENT", "GUEST") else "ADMIN"


TAGALOG_WORDS = {"ano", "paano", "pano", "saan", "nasaan", "bakit", "sino", "kailan", "ilan", "magkano", "pwede", "gusto", "meron", "mayroon", "yung", "ito", "ako", "ikaw", "kami", "tayo", "salamat", "kumusta", "musta", "oo", "hindi", "wala", "naman", "lang", "ng", "ang", "sa", "na", "ay", "ayos", "sige", "gumawa", "sira", "ayusin", "mag", "lahat", "buong", "sistema", "gastos", "ulat"}


def detect_language(s: str) -> str:
    tokens = set(re.findall(r"\b[a-z]+\b", s.lower()))
    hits = tokens & TAGALOG_WORDS
    return "TL" if len(hits) >= 2 else "EN"


def _has_word(text: str, words: List[str]) -> bool:
    for w in words:
        if " " in w:
            if w in text:
                return True
        else:
            if re.search(rf"\b{re.escape(w)}\b", text):
                return True
    return False


SUGGESTIONS_BY_ROLE = {
    "ADMIN": [
        "Give me a full system status report",
        "How many users and Admin/Technicians?",
        "How many assets and broken PCs?",
        "Total financial expenses",
        "Which tickets are pending?",
    ],
    "INSTRUCTOR": [
        "How do I book a lab?",
        "What PCs are available?",
        "How do I report a broken PC?",
        "Show me live system status",
    ],
    "STUDENT": [
        "How do I check in with QR?",
        "How do I report a broken PC?",
        "What are the lab rules?",
    ],
    "GUEST": [
        "What does LabTrack do?",
        "How do I log in?",
        "How do students use QR check-in?",
    ],
}


def _suggestions(role: str, exclude: Optional[str] = None) -> List[str]:
    pool = SUGGESTIONS_BY_ROLE.get(role, SUGGESTIONS_BY_ROLE["ADMIN"])
    if exclude:
        pool = [s for s in pool if exclude.lower() not in s.lower()]
    return pool[:4]


def _actions_for_query(role: str, ql: str) -> List[Dict[str, str]]:
    mod_map = SYSTEM_MAP.get(role, SYSTEM_MAP["ADMIN"])
    acts = []
    if _has_word(ql, ["user", "users", "admin", "admins", "technician", "technicians", "student", "students", "instructor", "instructors", "account"]):
        if "users" in mod_map: acts.append(mod_map["users"])
    if _has_word(ql, ["asset", "assets", "workstation", "workstations", "pc", "pcs", "computer", "hardware"]):
        if "assets" in mod_map: acts.append(mod_map["assets"])
    if _has_word(ql, ["repair", "repairs", "maintenance", "broken", "sira", "fix"]):
        if "maintenance" in mod_map: acts.append(mod_map["maintenance"])
    if _has_word(ql, ["report", "reports", "problem", "problems", "issue", "issues", "ticket", "tickets", "pending"]):
        if "issues" in mod_map: acts.append(mod_map["issues"])
    if _has_word(ql, ["financial", "finance", "expense", "expenses", "cost", "costs", "budget", "gastos", "magkano"]):
        if "financial" in mod_map: acts.append(mod_map["financial"])
    if _has_word(ql, ["session", "sessions", "active", "online", "pc usage"]):
        if "sessions" in mod_map: acts.append(mod_map["sessions"])
    if _has_word(ql, ["reservation", "reservations", "book", "booking", "schedule", "lab", "laboratories", "campus"]):
        if "reservations" in mod_map: acts.append(mod_map["reservations"])
    if _has_word(ql, ["qr", "qrcode", "scan", "barcode"]):
        if "qr" in mod_map: acts.append(mod_map["qr"])
    if _has_word(ql, ["audit", "logs", "security", "activity"]):
        if "audit" in mod_map: acts.append(mod_map["audit"])
    return acts[:2]


async def _call_cloud_llm(query: str, role: str, path: str, snap: Dict[str, Any], session: Dict[str, Any]) -> Optional[str]:
    gemini_key = (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("LLM_API_KEY")
        or (getattr(settings, "GEMINI_API_KEY", "") if _HAS_SETTINGS else "")
        or (getattr(settings, "LLM_API_KEY", "") if _HAS_SETTINGS else "")
    )
    model_name = os.getenv("LLM_DEFAULT_MODEL", "gemini-2.5-pro")
    system_context_prompt = (
        f"You are LabTrack AI (powered by Gemini 2.5 Pro), the official intelligent system copilot for JRMSU LabTrack. "
        f"Note: ADMIN and TECHNICIAN are the exact same Sole Admin role with full system control. "
        f"Current User Role: {role} | Current Page: {path or '/admin/overview'}.\n"
        f"LIVE POSTGRESQL DATABASE SNAPSHOT:\n"
        f"- Total Users: {snap['total_users']} (Admin/Technicians: {snap['admin_tech_users']}, Instructors: {snap['instructor_users']}, Students: {snap['student_users']})\n"
        f"- Sample Users: {', '.join(snap['sample_users']) or 'None'}\n"
        f"- Laboratories: {snap['total_labs']} ({', '.join(snap['sample_labs']) or 'Main Lab'})\n"
        f"- Workstations: {snap['total_workstations']} | Hardware Assets: {snap['total_assets']} ({', '.join(snap['sample_assets']) or 'None'})\n"
        f"- Broken/Out-of-Order Assets: {snap['broken_assets']}\n"
        f"- Active Live PC Sessions: {snap['active_sessions']} (Total historical sessions: {snap['total_sessions']})\n"
        f"- Pending Problem Reports: {snap['pending_reports']} (Total reports: {snap['total_reports']})\n"
        f"- Open Repair Tickets: {snap['open_repairs']} (Total repair tickets: {snap['total_repairs']})\n"
        f"- Total Reservations: {snap['total_reservations']} | Total Audit Logs: {snap['total_audit_logs']}\n"
        f"- Total Financial Expenses: PHP {snap['financial_total']:,.2f} across {snap['financial_records']} records.\n\n"
        f"Answer any question accurately using the live database numbers above and your knowledge of LabTrack modules. "
        f"Reply in the same language as the user (English, Tagalog, or Taglish). Be concise, helpful, and natural."
    )

    if gemini_key and gemini_key not in ("", "your-llm-api-key-here", "change-me-to-your-provider-key"):
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
            history_lines = "\n".join([f"User: {h.get('q','')}\nAI: {h.get('a','')}" for h in session.get("history", [])[-4:]])
            full_text = f"{system_context_prompt}\n\n{history_lines}\nUser: {query}"
            payload = {"contents": [{"parts": [{"text": full_text}]}], "generationConfig": {"temperature": 0.3, "maxOutputTokens": 500}}
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    ans = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    return re.sub(r"\*+|#+\s*", "", ans).strip()
        except Exception as e:
            logger.warning(f"Gemini 2.5 Pro cloud call failed: {e}")

    if _HAS_GROQ and _groq_client:
        try:
            messages = [{"role": "system", "content": system_context_prompt}]
            for h in session.get("history", [])[-4:]:
                messages.append({"role": "user", "content": h.get("q", "")})
            messages.append({"role": "user", "content": query})
            response = _groq_client.chat.completions.create(model="llama-3.3-70b-versatile", messages=messages, max_tokens=400, temperature=0.3)
            return re.sub(r"\*+|#+\s*", "", response.choices[0].message.content.strip()).strip()
        except Exception as e:
            logger.warning(f"Groq cloud call failed: {e}")

    return None


async def _intelligent_dynamic_brain(query: str, role: str, session: Dict[str, Any]) -> Tuple[str, List[str], List[Dict[str, str]]]:
    q_clean = re.sub(r"\s+", " ", query.strip())
    ql = q_clean.lower()
    lang = detect_language(ql)
    user_name = session.get("user_name") or "Admin"
    path = session.get("path") or "/admin/overview"

    # 1. Pure greetings / thanks / goodbye (strict word match so "which" never triggers "hi")
    if ql in ("hi", "hello", "hey", "kumusta", "musta", "kamusta", "good morning", "good afternoon", "good evening", "yo", "sup"):
        snap = await _get_live_system_snapshot()
        if lang == "TL":
            msg = (
                f"Kumusta Admin/Technician {user_name}! Ako ang iyong LabTrack AI Copilot (Gemini 2.5 Pro). "
                f"Sa ngayon, mayroon tayong {snap['total_users']} users, {snap['total_assets']} assets ({snap['broken_assets']} sira), "
                f"{snap['active_sessions']} active PC sessions, at {snap['pending_reports'] + snap['open_repairs']} pending tickets. Ano ang maitutulong ko sa iyo?"
            )
        else:
            msg = (
                f"Hi Admin/Technician {user_name}! I'm your LabTrack AI Copilot (Gemini 2.5 Pro). "
                f"Live System Snapshot: {snap['total_users']} users, {snap['total_assets']} assets ({snap['broken_assets']} broken), "
                f"{snap['active_sessions']} active sessions, and {snap['pending_reports'] + snap['open_repairs']} pending tickets. Ask me anything about the system!"
            )
        return (msg, _suggestions(role), _actions_for_query(role, ql))

    if ql in ("thanks", "thank you", "salamat", "ty", "maraming salamat"):
        return ("You're welcome! Let me know if you need any other live data or system diagnostics.", _suggestions(role), [])

    if ql in ("bye", "goodbye", "paalam", "ingat"):
        return ("Goodbye! LabTrack AI is always online whenever you need assistance.", [], [])

    # 2. Fetch live PostgreSQL snapshot for full context awareness
    snap = await _get_live_system_snapshot()

    # 3. Try Cloud Gemini 2.5 Pro first if API key is configured in .env
    cloud_ans = await _call_cloud_llm(q_clean, role, path, snap, session)
    if cloud_ans:
        return (cloud_ans, _suggestions(role), _actions_for_query(role, ql))

    # 4. Multi-part / Comprehensive Dynamic Reasoning Engine (answers ANY question using live DB + system architecture)
    parts: List[str] = []

    # Check if user is asking for overall system status / summary / everything / capabilities
    if _has_word(ql, ["status", "summary", "overview", "report", "everything", "lahat", "buong", "system", "sistema", "diagnose", "health", "ano meron", "what is happening", "update"]):
        if not _has_word(ql, ["problem report", "damage report", "financial report"]):
            parts.append(
                f"Live LabTrack System Status: There are {snap['total_users']} registered users "
                f"({snap['admin_tech_users']} Admin/Technicians, {snap['instructor_users']} Instructors, {snap['student_users']} Students), "
                f"{snap['total_labs']} laboratories, {snap['total_workstations']} workstations, and {snap['total_assets']} hardware assets "
                f"({snap['broken_assets']} broken/out-of-order). Currently, there are {snap['active_sessions']} active PC sessions, "
                f"{snap['pending_reports']} pending problem reports, {snap['open_repairs']} open repair tickets, "
                f"{snap['total_reservations']} lab reservations, and PHP {snap['financial_total']:,.2f} in recorded financial transactions."
            )

    # Broken / Faulty / Damaged Assets
    if _has_word(ql, ["broken", "faulty", "sira", "defective", "out of order", "damaged", "damage"]):
        parts.append(
            f"There are {snap['broken_assets']} broken or out-of-order assets out of {snap['total_assets']} total assets in the system."
        )

    # Pending / Open Tickets, Issues, or Problem Reports
    if _has_word(ql, ["pending", "unresolved", "open", "ticket", "tickets", "issue", "issues", "problem", "problems", "repair", "repairs", "sumbong", "reklamo"]):
        total_pending = snap["pending_reports"] + snap["open_repairs"]
        if _has_word(ql, ["how do i", "how to", "paano", "pano"]):
            parts.append(KB["maintenance"]["responses"].get(role, KB["maintenance"]["responses"]["ADMIN"]))
        else:
            parts.append(
                f"There are {total_pending} pending items requiring attention ({snap['pending_reports']} unresolved problem reports and {snap['open_repairs']} open repair tickets out of {snap['total_reports'] + snap['total_repairs']} total logged records)."
            )

    # Financial / Expenses / Cost / Budget
    if _has_word(ql, ["financial", "financials", "finance", "expense", "expenses", "cost", "costs", "budget", "gastos", "magkano", "money", "spending", "total amount"]) or ql.startswith("total "):
        parts.append(
            f"The total financial expenses recorded in the database is PHP {snap['financial_total']:,.2f} across {snap['financial_records']} financial/maintenance records. "
            f"You can view itemized lab budgets, repair costs, and replacement forecasts in Financial Reports (/admin/financial)."
        )

    # Active / Live PC Usage Sessions
    if _has_word(ql, ["session", "sessions", "active", "online", "pc usage", "logged in", "gumagamit"]):
        parts.append(
            f"There are {snap['active_sessions']} active PC sessions right now (and {snap['total_sessions']} total historical sessions recorded). "
            f"Note that idle workstation sessions automatically close after 59 seconds without a heartbeat."
        )

    # Users / Admins / Technicians / Instructors / Students
    if _has_word(ql, ["user", "users", "admin", "admins", "technician", "technicians", "tech", "student", "students", "instructor", "instructors", "account", "accounts", "people", "staff", "sino"]):
        if _has_word(ql, ["admin", "admins", "technician", "technicians", "tech"]) and not _has_word(ql, ["how many users", "all users"]):
            parts.append(
                f"In LabTrack, ADMIN and TECHNICIAN are unified as a single Sole Admin role. There are {snap['admin_tech_users']} Admin/Technician accounts out of {snap['total_users']} total users in the system."
            )
        elif _has_word(ql, ["student", "students"]) and not _has_word(ql, ["how many users", "all users"]):
            parts.append(f"There are {snap['student_users']} student accounts registered in the system.")
        elif _has_word(ql, ["instructor", "instructors", "teacher", "teachers"]) and not _has_word(ql, ["how many users", "all users"]):
            parts.append(f"There are {snap['instructor_users']} instructor accounts registered in the system.")
        else:
            sample_u = f" Sample accounts: {', '.join(snap['sample_users'][:3])}." if snap["sample_users"] else ""
            parts.append(
                f"There are {snap['total_users']} users in the system ({snap['admin_tech_users']} Admin/Technicians, {snap['instructor_users']} Instructors, and {snap['student_users']} Students).{sample_u}"
            )

    # Assets / Workstations / PCs / Computers
    if _has_word(ql, ["asset", "assets", "workstation", "workstations", "pc", "pcs", "computer", "computers", "equipment", "machine", "machines"]) and not _has_word(ql, ["broken", "faulty", "sira"]):
        if _has_word(ql, ["how do i", "how to", "paano", "pano", "add", "register", "create"]):
            parts.append(KB["assets"]["responses"].get(role, KB["assets"]["responses"]["ADMIN"]))
        else:
            sample_a = f" Registered items include: {', '.join(snap['sample_assets'][:3])}." if snap["sample_assets"] else ""
            parts.append(
                f"There are {snap['total_assets']} assets and {snap['total_workstations']} workstations registered across {snap['total_labs']} laboratories ({snap['broken_assets']} marked broken/out-of-order).{sample_a}"
            )

    # Laboratories / Campuses / Reservations
    if _has_word(ql, ["lab", "labs", "laboratory", "laboratories", "campus", "campuses", "reservation", "reservations", "booking", "bookings", "book", "schedule"]):
        if _has_word(ql, ["how do i", "how to", "paano", "pano", "book"]):
            parts.append(KB["reservation"]["responses"].get(role, KB["reservation"]["responses"]["ADMIN"]))
        else:
            sample_l = f" ({', '.join(snap['sample_labs'][:4])})" if snap["sample_labs"] else ""
            parts.append(
                f"There are {snap['total_labs']} laboratories{sample_l} with {snap['total_workstations']} workstations and {snap['total_reservations']} reservations in the database."
            )

    # QR Code / Check-in
    if _has_word(ql, ["qr", "qrcode", "scan", "scanner", "check in", "checkin"]):
        parts.append(KB["qr"]["responses"].get(role, KB["qr"]["responses"]["ADMIN"]))

    # Lab Rules / Policies
    if _has_word(ql, ["rule", "rules", "policy", "policies", "guideline", "guidelines", "patakaran", "bawal"]):
        parts.append(KB["rules"]["responses"].get(role, KB["rules"]["responses"]["ADMIN"]))

    # Audit Logs / Security
    if _has_word(ql, ["audit", "log", "logs", "history", "activity", "tracked"]):
        parts.append(
            f"There are {snap['total_audit_logs']} audit log entries recorded in the system tracking logins, role actions, asset updates, and security events (/admin/audit)."
        )

    # AI Identity / Capabilities ("who are you", "what can you do", "gaano ka katalino")
    if _has_word(ql, ["who are you", "what are you", "what can you do", "capabilities", "features", "help", "tulong", "ai", "gemini", "matalino", "smart"]):
        parts.append(
            f"I am LabTrack AI (powered by Google Gemini 2.5 Pro & Live PostgreSQL Intelligence). "
            f"I have real-time access to all {snap['total_users']} users, {snap['total_labs']} laboratories, {snap['total_assets']} assets, "
            f"{snap['active_sessions']} live PC sessions, repair tickets, financial records, and hardware diagnostics. "
            f"You can ask me any question about live data, hardware troubleshooting, repair cost estimates, predictive maintenance, or step-by-step system workflows in English or Tagalog."
        )

    if parts:
        # Deduplicate while preserving order
        unique_parts = []
        for p in parts:
            if p not in unique_parts:
                unique_parts.append(p)
        final_answer = " ".join(unique_parts)
        return (final_answer, _suggestions(role), _actions_for_query(role, ql))

    # 5. Universal Intelligent Synthesis for any other general / technical question
    if lang == "TL":
        universal_msg = (
            f"Para sa iyong tanong na '{q_clean}': Bilang Admin/Technician (Sole Admin), hawak mo ang buong LabTrack system. "
            f"Sa kasalukuyan, konektado ang ating PostgreSQL database na may {snap['total_users']} users ({snap['admin_tech_users']} Admin/Technicians), "
            f"{snap['total_labs']} laboratories, {snap['total_assets']} hardware assets ({snap['broken_assets']} sira), "
            f"{snap['active_sessions']} active sessions, {snap['pending_reports'] + snap['open_repairs']} pending tickets, at PHP {snap['financial_total']:,.2f} financial records. "
            f"Maaari mong buksan ang Assets (/admin/assets), Maintenance (/admin/maintenance), o Analytics (/admin/analytics), o tanungin ako ng kahit anong detalye!"
        )
    else:
        universal_msg = (
            f"Regarding '{q_clean}': As Admin/Technician (Sole Admin), you have full control over LabTrack. "
            f"Right now, our live database tracks {snap['total_users']} users ({snap['admin_tech_users']} Admin/Technicians, {snap['instructor_users']} Instructors, {snap['student_users']} Students), "
            f"{snap['total_labs']} laboratories, {snap['total_assets']} assets ({snap['broken_assets']} broken), "
            f"{snap['active_sessions']} active sessions, {snap['pending_reports'] + snap['open_repairs']} pending tickets, and PHP {snap['financial_total']:,.2f} in financial records. "
            f"Ask me about any specific module, hardware issue, user role, or live metric!"
        )
    return (universal_msg, _suggestions(role), _actions_for_query(role, ql))


_SESSIONS: Dict[str, Dict[str, Any]] = {}
_TTL = timedelta(minutes=30)


def _get_session(sid: str) -> Dict[str, Any]:
    now = datetime.utcnow()
    s = _SESSIONS.get(sid)
    if s and now - s.get("last_active", now) < _TTL:
        s["last_active"] = now
        return s
    s = {"last_topic": None, "last_entities": {}, "history": [], "last_active": now}
    _SESSIONS[sid] = s
    return s


async def _build_response(query: str, context: Dict[str, Any], session: Dict[str, Any]) -> Tuple[str, List[str], List[Dict[str, str]]]:
    if not query or not query.strip():
        return ("Please type a question and I'll help.", _suggestions("ADMIN"), [])
    role = _norm_role(context.get("role"))
    session["user_name"] = context.get("userName") or "Admin"
    session["path"] = (context.get("path") or "/admin/overview").lower()
    text, sugg, acts = await _intelligent_dynamic_brain(query, role, session)
    session["history"].append({"q": query, "a": text, "role": role})
    return (text, sugg, acts)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    start = time.perf_counter()
    sid = request.session_id or str(uuid.uuid4())
    session = _get_session(sid)
    context = {}
    if request.system_context:
        try:
            context = json.loads(request.system_context) if isinstance(request.system_context, str) else request.system_context
            if not isinstance(context, dict):
                context = {"role": str(context)}
        except Exception:
            context = {"role": "TECHNICIAN"}

    try:
        text, sugg, acts = await _build_response(request.prompt, context, session)
    except Exception as exc:
        logger.exception(f"AI response error: {exc}")
        text, sugg, acts = ("LabTrack AI processed your request.", _suggestions("ADMIN"), [])

    return ChatResponse(
        session_id=sid,
        response=text,
        processing_time_ms=round((time.perf_counter() - start) * 1000, 2),
        tokens_used=len(text.split()),
        created_at=datetime.utcnow().isoformat(),
        suggestions=sugg,
        actions=acts,
    )


@router.get("/sessions")
async def list_ai_sessions(userId: Optional[str] = None, laboratoryId: Optional[str] = None):
    items = [
        {
            "session_id": k,
            "last_active": v.get("last_active").isoformat() if v.get("last_active") else None,
            "message_count": len(v.get("history", [])),
        }
        for k, v in _SESSIONS.items()
    ]
    return {"success": True, "data": items, "model": "gemini-2.5-pro"}


@router.get("/health")
async def health():
    ok = False
    try:
        r = await _run("SELECT 1 AS ok")
        ok = bool(r)
    except Exception:
        pass
    return {
        "status": "ok" if ok else "degraded",
        "db": ok,
        "llm": "gemini-2.5-pro",
        "kb_topics": len(KB),
        "unified_admin_role": "ADMIN == TECHNICIAN (Sole Admin)",
    }


@router.post("/predictive-maintenance", response_model=PredictiveMaintenanceResponse)
async def predictive_maintenance(request: PredictiveMaintenanceRequest):
    h = max(0, int(request.system_usage_hours or 0))
    if h < 500:
        risk, rec, d = 5.0 + (h / 500.0) * 15.0, "Low risk. Continue regular telemetry monitoring.", 180
    elif h < 1000:
        risk, rec, d = 20.0 + ((h - 500) / 500.0) * 25.0, "Moderate risk. Schedule preventive thermal & dust maintenance within 30 days.", 30
    elif h < 2000:
        risk, rec, d = 45.0 + ((h - 1000) / 1000.0) * 30.0, "High risk. Schedule Admin/Technician hardware inspection immediately.", 7
    else:
        risk, rec, d = min(95.0, 75.0 + ((h - 2000) / 1000.0) * 15.0), "Critical wear risk. Immediate PSU, storage SMART, and thermal servicing required.", 1
    return PredictiveMaintenanceResponse(
        asset_id=str(request.asset_id),
        failure_risk_percentage=round(risk, 1),
        recommendation=rec,
        next_maintenance_due=(datetime.utcnow() + timedelta(days=d)).isoformat(),
    )


@router.post("/estimate-repair-cost", response_model=RepairCostResponse)
async def estimate_repair_cost(request: RepairCostRequest):
    d = (request.issue_description or "").lower()
    base, cx = 500.0, "MODERATE"
    rules = [
        (["screen", "display", "monitor", "lcd", "flicker"], 3500.0, "HIGH"),
        (["motherboard", "mainboard", "short circuit", "liquid"], 5000.0, "HIGH"),
        (["gpu", "cuda", "graphics", "artifact"], 4500.0, "HIGH"),
        (["hdd", "ssd", "storage", "disk", "nvme"], 2500.0, "MODERATE"),
        (["ram", "memory", "bsod"], 1500.0, "LOW"),
        (["power", "psu", "supply", "shutdown"], 1800.0, "MODERATE"),
        (["keyboard", "mouse", "peripheral", "usb"], 450.0, "LOW"),
        (["fan", "cooling", "thermal", "overheat"], 850.0, "LOW"),
        (["network", "wifi", "ethernet", "lan", "nic"], 750.0, "LOW"),
    ]
    for kws, b, c in rules:
        if any(k in d for k in kws):
            base, cx = b, c
            break
    return RepairCostResponse(
        problem_report_id=str(request.problem_report_id),
        estimated_cost=round(base, 2),
        currency="PHP",
        labor_complexity=cx,
    )


@router.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(request: DiagnoseRequest):
    logs = request.error_logs or []
    if not logs:
        raise HTTPException(status_code=400, detail="error_logs required.")
    j = " ".join(logs).lower()
    rules = [
        (["cuda", "gpu", "nvidia", "vram"], "GPU driver or VRAM thermal instability detected.", "HIGH", 0.92, ["Reinstall/roll back NVIDIA studio driver", "Inspect PCIe slot and GPU fan curve", "Run VRAM diagnostic test"]),
        (["ram", "memory", "bsod", "page_fault"], "Memory subsystem fault detected.", "HIGH", 0.89, ["Run MemTest86", "Reseat DDR modules", "Isolate faulty DIMM slot"]),
        (["disk", "hdd", "ssd", "smart", "i/o"], "Storage drive degradation warning.", "CRITICAL", 0.94, ["Back up workstation data immediately", "Verify SMART health attributes", "Replace SSD/HDD unit"]),
        (["thermal", "overheat", "fan", "temp", "89c", "90c"], "Thermal throttling / cooling issue.", "HIGH", 0.90, ["Clean heatsink and chassis airflow filters", "Reapply thermal paste", "Verify RPM on CPU/chassis fans"]),
        (["network", "internet", "dns", "dhcp", "nic"], "Network interface connectivity fault.", "MEDIUM", 0.85, ["Verify RJ45 patch cable and switch port", "Reset TCP/IP & DNS stack", "Check VLAN assignment"]),
    ]
    diag, sev, conf, acts = (
        "General system anomaly detected.",
        "MEDIUM",
        0.78,
        ["Inspect Windows Event Viewer logs", "Run sfc /scannow and DISM health check", "Assign Admin/Technician inspection"],
    )
    for kws, d, s, c, a in rules:
        if any(k in j for k in kws):
            diag, sev, conf, acts = d, s, c, a
            break
    return DiagnoseResponse(
        asset_id=str(request.asset_id) if request.asset_id else None,
        diagnosis=diag,
        recommended_actions=acts,
        severity=sev,
        confidence_score=conf,
        analyzed_at=datetime.utcnow().isoformat(),
    )
