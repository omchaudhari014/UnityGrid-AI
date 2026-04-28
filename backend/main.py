from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


DB_PATH = Path(__file__).with_name("unitygrid.db")

Urgency = Literal["critical", "high", "medium", "low"]
Category = Literal["Water", "Medical", "Food", "Education", "Shelter", "Transport", "Other"]

PRIORITY_ORDER: dict[str, int] = {"critical": 4, "high": 3, "medium": 2, "low": 1}
SEVERITY_TO_SCORE: dict[str, float] = {"critical": 1.0, "high": 0.75, "medium": 0.5, "low": 0.25}

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Water": ("water", "drinking water", "borewell", "tank", "hydration", "pani", "clean water"),
    "Medical": ("medical", "medicine", "doctor", "clinic", "hospital", "health", "first aid", "nursing"),
    "Food": ("food", "ration", "nutrition", "malnutrition", "meal", "hunger", "groceries"),
    "Education": ("school", "teaching", "education", "supplies", "books", "uniform", "training"),
    "Shelter": ("toilet", "sanitation", "shelter", "housing", "repair", "hygiene", "washroom"),
    "Transport": ("transport", "ambulance", "vehicle", "travel", "pickup", "route"),
}

URGENCY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "critical": ("critical", "emergency", "immediately", "urgent", "life threatening", "severe"),
    "high": ("high", "priority", "within 24", "asap", "serious"),
    "medium": ("medium", "soon", "this week"),
    "low": ("low", "routine", "whenever"),
}

AREA_DEPRIVATION_INDEX: dict[str, float] = {
    "Hadapsar": 0.78,
    "Yerawada": 0.82,
    "Kondhwa": 0.74,
    "Bibwewadi": 0.62,
    "Wanawadi": 0.58,
    "Kothrud": 0.45,
    "Shivajinagar": 0.52,
}

AREA_NEIGHBORS: dict[str, set[str]] = {
    "Hadapsar": {"Kondhwa", "Wanawadi", "Bibwewadi"},
    "Yerawada": {"Shivajinagar", "Kothrud"},
    "Kondhwa": {"Hadapsar", "Bibwewadi", "Wanawadi"},
    "Bibwewadi": {"Kondhwa", "Hadapsar", "Kothrud"},
    "Wanawadi": {"Hadapsar", "Kondhwa"},
    "Kothrud": {"Bibwewadi", "Shivajinagar", "Yerawada"},
    "Shivajinagar": {"Yerawada", "Kothrud"},
}

CATEGORY_DEFAULT_NEED_NAME: dict[str, str] = {
    "Water": "Clean drinking water support",
    "Medical": "Emergency medical care access",
    "Food": "Food and nutrition support",
    "Education": "School and education support",
    "Shelter": "Sanitation and shelter repair",
    "Transport": "Emergency transport assistance",
    "Other": "General community aid support",
}

CATEGORY_DEFAULT_TASK: dict[str, str] = {
    "Water": "Coordinate immediate clean water supply and distribution.",
    "Medical": "Assist with medical camp coordination and patient transport.",
    "Food": "Support meal distribution and nutrition supply delivery.",
    "Education": "Distribute educational supplies and student support kits.",
    "Shelter": "Coordinate sanitation repair and temporary shelter support.",
    "Transport": "Arrange local transport for urgent cases.",
    "Other": "Coordinate ground response with local volunteers.",
}


class AnalyzeReportRequest(BaseModel):
    area: str = Field(min_length=2, max_length=100)
    content: str = Field(min_length=20)


class ExtractedNeed(BaseModel):
    name: str
    category: Category
    urgency: Urgency
    affected_count: int
    volunteer_task: str
    cni_score: float


class AnalyzeReportResponse(BaseModel):
    needs: list[ExtractedNeed]
    summary: str
    total_affected: int


class ReportCreate(BaseModel):
    organisation: str = Field(min_length=2, max_length=150)
    area: str = Field(min_length=2, max_length=100)
    content: str = Field(min_length=20)
    report_date: str | None = None


class VolunteerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    skills: str = Field(min_length=2, max_length=240)
    area: str = Field(min_length=2, max_length=100)
    hours_per_week: int = Field(ge=1, le=80)
    reliability_score: float = Field(default=0.75, ge=0.1, le=1.0)
    available: bool = True


class CompleteAssignmentRequest(BaseModel):
    completion_note: str | None = None


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organisation TEXT NOT NULL,
                area TEXT NOT NULL,
                content TEXT NOT NULL,
                report_date TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS volunteers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                skills TEXT NOT NULL,
                area TEXT NOT NULL,
                hours_per_week INTEGER NOT NULL,
                reliability_score REAL NOT NULL DEFAULT 0.75,
                available INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS needs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                urgency TEXT NOT NULL,
                affected_count INTEGER NOT NULL,
                volunteer_task TEXT NOT NULL,
                area TEXT NOT NULL,
                cni_score REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                assigned_volunteer_id INTEGER,
                created_at TEXT NOT NULL,
                resolved_at TEXT,
                FOREIGN KEY(report_id) REFERENCES reports(id),
                FOREIGN KEY(assigned_volunteer_id) REFERENCES volunteers(id)
            );

            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                need_id INTEGER NOT NULL,
                volunteer_id INTEGER NOT NULL,
                match_score REAL NOT NULL,
                rationale TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'assigned',
                created_at TEXT NOT NULL,
                completed_at TEXT,
                completion_note TEXT,
                FOREIGN KEY(need_id) REFERENCES needs(id),
                FOREIGN KEY(volunteer_id) REFERENCES volunteers(id)
            );

            CREATE TABLE IF NOT EXISTS area_stats (
                area TEXT PRIMARY KEY,
                total_needs INTEGER NOT NULL DEFAULT 0,
                total_assigned INTEGER NOT NULL DEFAULT 0
            );
            """
        )


def seed_if_empty() -> None:
    with get_conn() as conn:
        current = conn.execute("SELECT COUNT(*) AS c FROM volunteers").fetchone()["c"]
        if current > 0:
            return

        for volunteer in (
            ("Priya Sharma", "medical, first aid", "Hadapsar", 10, 0.86),
            ("Arun Kulkarni", "teaching, education", "Kothrud", 8, 0.78),
            ("Meena Joshi", "nutrition, childcare", "Yerawada", 12, 0.84),
            ("Ravi Desai", "logistics, water, sanitation", "Any", 15, 0.81),
            ("Sunita Patil", "elderly care, nursing", "Bibwewadi", 6, 0.8),
        ):
            conn.execute(
                """
                INSERT INTO volunteers (name, skills, area, hours_per_week, reliability_score, available, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (*volunteer, now_iso()),
            )


def extract_first_int(text: str) -> int | None:
    match = re.search(r"\b(\d{1,4})\b", text)
    if not match:
        return None
    return int(match.group(1))


def infer_urgency(text: str, affected_count: int) -> Urgency:
    lowered = text.lower()
    for urgency in ("critical", "high", "medium", "low"):
        for token in URGENCY_KEYWORDS[urgency]:
            if token in lowered:
                return urgency  # type: ignore[return-value]

    if affected_count >= 25:
        return "critical"
    if affected_count >= 12:
        return "high"
    if affected_count >= 6:
        return "medium"
    return "low"


def infer_category(sentence: str) -> list[str]:
    lowered = sentence.lower()
    found: list[str] = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(k in lowered for k in keywords):
            found.append(category)
    return found


def compute_cni(area: str, urgency: Urgency, affected_count: int) -> float:
    severity = SEVERITY_TO_SCORE[urgency]
    affected_norm = min(1.0, affected_count / 50.0)
    deprivation = AREA_DEPRIVATION_INDEX.get(area, 0.55)
    cni = (severity * 0.5) + (affected_norm * 0.3) + (deprivation * 0.2)
    return round(cni, 2)


def analyze_content(area: str, content: str) -> AnalyzeReportResponse:
    raw_segments = [s.strip() for s in re.split(r"[\n\.]+", content) if len(s.strip()) > 10]
    aggregate: dict[str, dict[str, object]] = {}

    for segment in raw_segments:
        categories = infer_category(segment)
        if not categories:
            continue

        affected = extract_first_int(segment) or 3
        urgency = infer_urgency(segment, affected)

        for category in categories:
            if category not in aggregate:
                aggregate[category] = {
                    "affected_count": 0,
                    "urgency": "low",
                    "evidence": [],
                }

            aggregate[category]["affected_count"] = int(aggregate[category]["affected_count"]) + affected
            aggregate[category]["evidence"] = list(aggregate[category]["evidence"]) + [segment]

            existing_urgency = str(aggregate[category]["urgency"])
            if PRIORITY_ORDER[urgency] > PRIORITY_ORDER[existing_urgency]:
                aggregate[category]["urgency"] = urgency

    if not aggregate:
        fallback_affected = extract_first_int(content) or 5
        fallback_urgency = infer_urgency(content, fallback_affected)
        aggregate["Other"] = {
            "affected_count": fallback_affected,
            "urgency": fallback_urgency,
            "evidence": [content[:180]],
        }

    extracted: list[ExtractedNeed] = []
    total_affected = 0
    for category, payload in aggregate.items():
        affected_count = int(payload["affected_count"])
        urgency = str(payload["urgency"])
        cni = compute_cni(area, urgency, affected_count)
        total_affected += affected_count

        evidence = list(payload["evidence"])
        headline = CATEGORY_DEFAULT_NEED_NAME.get(category, CATEGORY_DEFAULT_NEED_NAME["Other"])
        if evidence:
            first_line = evidence[0]
            if len(first_line) > 50:
                first_line = first_line[:50].strip() + "…"
            headline = f"{headline} ({first_line})"

        extracted.append(
            ExtractedNeed(
                name=headline,
                category=category if category in CATEGORY_DEFAULT_NEED_NAME else "Other",
                urgency=urgency if urgency in PRIORITY_ORDER else "low",
                affected_count=affected_count,
                volunteer_task=CATEGORY_DEFAULT_TASK.get(category, CATEGORY_DEFAULT_TASK["Other"]),
                cni_score=cni,
            )
        )

    extracted.sort(key=lambda n: (PRIORITY_ORDER[n.urgency], n.affected_count), reverse=True)
    summary = f"Detected {len(extracted)} need categories in {area}; estimated {total_affected} people affected."
    return AnalyzeReportResponse(needs=extracted, summary=summary, total_affected=total_affected)


def parse_skill_tokens(skills_text: str) -> set[str]:
    tokens = re.split(r"[,\s/]+", skills_text.lower())
    return {t.strip() for t in tokens if t.strip()}


def proximity_score(need_area: str, volunteer_area: str) -> float:
    va = volunteer_area.strip()
    if va.lower() == "any":
        return 0.8
    if va.lower() == need_area.lower():
        return 1.0
    neighbors = AREA_NEIGHBORS.get(need_area, set())
    if va in neighbors:
        return 0.75
    return 0.35


def volunteer_capacity(hours_per_week: int) -> int:
    return max(1, hours_per_week // 4)


def current_load(conn: sqlite3.Connection, volunteer_id: int) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS c
        FROM assignments
        WHERE volunteer_id = ?
        AND status IN ('assigned', 'accepted', 'in_progress')
        """,
        (volunteer_id,),
    ).fetchone()
    return int(row["c"])


def fairness_bonus(conn: sqlite3.Connection, area: str) -> float:
    row = conn.execute("SELECT total_needs, total_assigned FROM area_stats WHERE area = ?", (area,)).fetchone()
    if not row:
        return 1.0

    total_needs = int(row["total_needs"])
    total_assigned = int(row["total_assigned"])
    if total_needs == 0:
        return 1.0

    coverage = min(1.0, total_assigned / total_needs)
    return round(1.0 - coverage, 3)


def ensure_area_stats_row(conn: sqlite3.Connection, area: str) -> None:
    conn.execute("INSERT OR IGNORE INTO area_stats (area, total_needs, total_assigned) VALUES (?, 0, 0)", (area,))


def score_match(conn: sqlite3.Connection, need_row: sqlite3.Row, volunteer_row: sqlite3.Row) -> tuple[float, str]:
    need_text = f"{need_row['name']} {need_row['category']} {need_row['volunteer_task']}".lower()
    need_tokens = parse_skill_tokens(need_text)
    volunteer_tokens = parse_skill_tokens(volunteer_row["skills"])

    overlap = len(need_tokens.intersection(volunteer_tokens))
    skill_score = min(1.0, overlap / 3.0) if overlap else 0.2

    prox_score = proximity_score(str(need_row["area"]), str(volunteer_row["area"]))

    capacity = volunteer_capacity(int(volunteer_row["hours_per_week"]))
    load = current_load(conn, int(volunteer_row["id"]))
    avail_score = max(0.2, 1.0 - (load / capacity))

    urgency_weight = {"critical": 1.0, "high": 0.75, "medium": 0.45, "low": 0.2}.get(str(need_row["urgency"]), 0.2)
    fairness = fairness_bonus(conn, str(need_row["area"]))
    reliability = float(volunteer_row["reliability_score"])

    score_0_to_1 = (
        (0.35 * prox_score)
        + (0.25 * skill_score)
        + (0.15 * avail_score)
        + (0.10 * reliability)
        + (0.10 * urgency_weight)
        + (0.05 * fairness)
    )
    score_percent = round(score_0_to_1 * 100, 2)

    rationale_bits = []
    rationale_bits.append("same-area proximity" if prox_score >= 0.95 else "nearby-area proximity" if prox_score >= 0.7 else "distance trade-off")
    rationale_bits.append("strong skill fit" if skill_score >= 0.66 else "partial skill fit")
    rationale_bits.append("good availability" if avail_score >= 0.6 else "limited availability")
    rationale = ", ".join(rationale_bits) + "."

    return score_percent, rationale


def increment_area_needs(conn: sqlite3.Connection, area: str, delta: int = 1) -> None:
    ensure_area_stats_row(conn, area)
    conn.execute("UPDATE area_stats SET total_needs = total_needs + ? WHERE area = ?", (delta, area))


def increment_area_assigned(conn: sqlite3.Connection, area: str, delta: int = 1) -> None:
    ensure_area_stats_row(conn, area)
    conn.execute("UPDATE area_stats SET total_assigned = total_assigned + ? WHERE area = ?", (delta, area))


def row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


app = FastAPI(
    title="UnityGrid AI Backend",
    version="1.0.0",
    description="Backend API for community need detection, volunteer matching, and fairness-aware dispatch.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    seed_if_empty()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "timestamp": now_iso()}


@app.post("/api/reports/analyze", response_model=AnalyzeReportResponse)
def analyze_report(payload: AnalyzeReportRequest) -> AnalyzeReportResponse:
    return analyze_content(area=payload.area, content=payload.content)


@app.post("/api/reports")
def create_report(payload: ReportCreate) -> dict:
    analysis = analyze_content(area=payload.area, content=payload.content)
    created_at = now_iso()

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO reports (organisation, area, content, report_date, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                payload.organisation,
                payload.area,
                payload.content,
                payload.report_date,
                created_at,
            ),
        )
        report_id = cursor.lastrowid

        for need in analysis.needs:
            conn.execute(
                """
                INSERT INTO needs (
                    report_id, name, category, urgency, affected_count, volunteer_task,
                    area, cni_score, status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
                """,
                (
                    report_id,
                    need.name,
                    need.category,
                    need.urgency,
                    need.affected_count,
                    need.volunteer_task,
                    payload.area,
                    need.cni_score,
                    created_at,
                ),
            )
            increment_area_needs(conn, payload.area)

    return {
        "report_id": report_id,
        "organisation": payload.organisation,
        "area": payload.area,
        "created_at": created_at,
        "extracted_need_count": len(analysis.needs),
        "analysis": analysis.model_dump(),
    }


@app.get("/api/needs")
def list_needs(
    area: str | None = None,
    urgency: str | None = None,
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    where: list[str] = []
    values: list[object] = []
    if area:
        where.append("area = ?")
        values.append(area)
    if urgency:
        where.append("urgency = ?")
        values.append(urgency.lower())
    if status:
        where.append("status = ?")
        values.append(status.lower())

    query = """
        SELECT n.*, v.name AS assigned_volunteer_name
        FROM needs n
        LEFT JOIN volunteers v ON v.id = n.assigned_volunteer_id
    """
    if where:
        query += " WHERE " + " AND ".join(where)
    query += """
        ORDER BY
            CASE urgency
                WHEN 'critical' THEN 4
                WHEN 'high' THEN 3
                WHEN 'medium' THEN 2
                ELSE 1
            END DESC,
            affected_count DESC,
            created_at DESC
        LIMIT ?
    """
    values.append(limit)

    with get_conn() as conn:
        rows = conn.execute(query, tuple(values)).fetchall()
        return {"count": len(rows), "items": [row_to_dict(r) for r in rows]}


@app.get("/api/dashboard/summary")
def dashboard_summary() -> dict:
    with get_conn() as conn:
        open_needs = conn.execute(
            "SELECT COUNT(*) AS c FROM needs WHERE status IN ('open', 'active', 'unmet')"
        ).fetchone()["c"]
        critical_needs = conn.execute(
            "SELECT COUNT(*) AS c FROM needs WHERE status IN ('open', 'active', 'unmet') AND urgency = 'critical'"
        ).fetchone()["c"]
        volunteers_ready = conn.execute(
            "SELECT COUNT(*) AS c FROM volunteers WHERE available = 1"
        ).fetchone()["c"]
        resolved_7d = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM needs
            WHERE status = 'resolved'
            AND resolved_at IS NOT NULL
            AND datetime(replace(resolved_at, 'Z', '')) >= datetime(?)
            """,
            ((datetime.utcnow() - timedelta(days=7)).replace(microsecond=0).isoformat(),),
        ).fetchone()["c"]

        top_needs = conn.execute(
            """
            SELECT name, area, category, urgency, affected_count, cni_score, status
            FROM needs
            WHERE status IN ('open', 'active', 'unmet')
            ORDER BY
                CASE urgency
                    WHEN 'critical' THEN 4
                    WHEN 'high' THEN 3
                    WHEN 'medium' THEN 2
                    ELSE 1
                END DESC,
                affected_count DESC
            LIMIT 8
            """
        ).fetchall()

        category_rows = conn.execute(
            "SELECT category, COUNT(*) AS total FROM needs GROUP BY category ORDER BY total DESC"
        ).fetchall()

        area_rows = conn.execute(
            """
            SELECT area, COUNT(*) AS total_reports, AVG(cni_score) AS avg_cni
            FROM needs
            GROUP BY area
            ORDER BY total_reports DESC
            """
        ).fetchall()

    return {
        "open_needs": int(open_needs),
        "critical_urgency": int(critical_needs),
        "volunteers_ready": int(volunteers_ready),
        "resolved_7d": int(resolved_7d),
        "top_needs": [row_to_dict(r) for r in top_needs],
        "category_breakdown": [row_to_dict(r) for r in category_rows],
        "area_breakdown": [row_to_dict(r) for r in area_rows],
    }


@app.get("/api/heatmap")
def heatmap() -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                n.area,
                COUNT(*) AS need_count,
                AVG(n.cni_score) AS avg_cni,
                COALESCE(a.total_assigned, 0) AS total_assigned,
                COALESCE(a.total_needs, 0) AS total_needs
            FROM needs n
            LEFT JOIN area_stats a ON a.area = n.area
            GROUP BY n.area
            ORDER BY avg_cni DESC, need_count DESC
            """
        ).fetchall()

    items = []
    for row in rows:
        data = row_to_dict(row)
        total_needs = max(1, int(data["total_needs"]))
        fairness_gap = round(1.0 - (int(data["total_assigned"]) / total_needs), 3)
        data["avg_cni"] = round(float(data["avg_cni"] or 0), 2)
        data["fairness_gap"] = fairness_gap
        items.append(data)

    return {"count": len(items), "items": items}


@app.post("/api/volunteers")
def create_volunteer(payload: VolunteerCreate) -> dict:
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO volunteers (name, skills, area, hours_per_week, reliability_score, available, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.name,
                payload.skills,
                payload.area,
                payload.hours_per_week,
                payload.reliability_score,
                1 if payload.available else 0,
                now_iso(),
            ),
        )
        volunteer_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM volunteers WHERE id = ?", (volunteer_id,)).fetchone()
    return {"volunteer": row_to_dict(row)}


@app.get("/api/volunteers")
def list_volunteers(available_only: bool = False) -> dict:
    query = "SELECT * FROM volunteers"
    params: tuple[object, ...] = ()
    if available_only:
        query += " WHERE available = 1"
    query += " ORDER BY created_at DESC"

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return {"count": len(rows), "items": [row_to_dict(r) for r in rows]}


@app.post("/api/matching/run")
def run_matching(max_assignments: int = Query(default=10, ge=1, le=100)) -> dict:
    with get_conn() as conn:
        needs = conn.execute(
            """
            SELECT *
            FROM needs
            WHERE status IN ('open', 'unmet')
            ORDER BY
                CASE urgency
                    WHEN 'critical' THEN 4
                    WHEN 'high' THEN 3
                    WHEN 'medium' THEN 2
                    ELSE 1
                END DESC,
                affected_count DESC,
                cni_score DESC
            """
        ).fetchall()

        volunteers = conn.execute(
            "SELECT * FROM volunteers WHERE available = 1 ORDER BY reliability_score DESC, hours_per_week DESC"
        ).fetchall()

        if not needs:
            return {"count": 0, "items": [], "message": "No open needs to match."}
        if not volunteers:
            return {"count": 0, "items": [], "message": "No available volunteers."}

        generated = []
        ephemeral_loads: dict[int, int] = {}

        for need in needs:
            if len(generated) >= max_assignments:
                break

            best_volunteer = None
            best_score = -1.0
            best_rationale = ""

            for volunteer in volunteers:
                vid = int(volunteer["id"])
                cap = volunteer_capacity(int(volunteer["hours_per_week"]))
                persistent_load = current_load(conn, vid)
                transient_load = ephemeral_loads.get(vid, 0)

                if (persistent_load + transient_load) >= cap:
                    continue

                score, rationale = score_match(conn, need, volunteer)
                if score > best_score:
                    best_score = score
                    best_volunteer = volunteer
                    best_rationale = rationale

            if best_volunteer is None or best_score < 35:
                continue

            created = now_iso()
            cur = conn.execute(
                """
                INSERT INTO assignments (need_id, volunteer_id, match_score, rationale, status, created_at)
                VALUES (?, ?, ?, ?, 'assigned', ?)
                """,
                (
                    int(need["id"]),
                    int(best_volunteer["id"]),
                    best_score,
                    best_rationale,
                    created,
                ),
            )
            assignment_id = cur.lastrowid

            conn.execute(
                "UPDATE needs SET status = 'active', assigned_volunteer_id = ? WHERE id = ?",
                (int(best_volunteer["id"]), int(need["id"])),
            )
            increment_area_assigned(conn, str(need["area"]), 1)

            vid = int(best_volunteer["id"])
            ephemeral_loads[vid] = ephemeral_loads.get(vid, 0) + 1

            generated.append(
                {
                    "assignment_id": assignment_id,
                    "volunteer": str(best_volunteer["name"]),
                    "volunteer_id": vid,
                    "match_score": best_score,
                    "assigned_need": str(need["name"]),
                    "need_id": int(need["id"]),
                    "area": str(need["area"]),
                    "rationale": best_rationale,
                }
            )

    return {"count": len(generated), "items": generated}


@app.get("/api/assignments")
def list_assignments(status: str | None = None, limit: int = Query(default=200, ge=1, le=1000)) -> dict:
    query = """
        SELECT
            a.*,
            n.name AS need_name,
            n.area AS need_area,
            n.category AS need_category,
            n.urgency AS need_urgency,
            v.name AS volunteer_name,
            v.skills AS volunteer_skills
        FROM assignments a
        JOIN needs n ON n.id = a.need_id
        JOIN volunteers v ON v.id = a.volunteer_id
    """
    params: list[object] = []
    if status:
        query += " WHERE a.status = ?"
        params.append(status.lower())
    query += " ORDER BY a.created_at DESC LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return {"count": len(rows), "items": [row_to_dict(r) for r in rows]}


@app.post("/api/assignments/{assignment_id}/complete")
def complete_assignment(assignment_id: int, payload: CompleteAssignmentRequest) -> dict:
    with get_conn() as conn:
        assignment = conn.execute("SELECT * FROM assignments WHERE id = ?", (assignment_id,)).fetchone()
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        if assignment["status"] == "completed":
            return {"message": "Assignment already completed", "assignment_id": assignment_id}

        completed_at = now_iso()
        conn.execute(
            """
            UPDATE assignments
            SET status = 'completed', completed_at = ?, completion_note = ?
            WHERE id = ?
            """,
            (completed_at, payload.completion_note, assignment_id),
        )
        conn.execute(
            """
            UPDATE needs
            SET status = 'resolved', resolved_at = ?
            WHERE id = ?
            """,
            (completed_at, assignment["need_id"]),
        )

    return {"message": "Assignment marked as completed", "assignment_id": assignment_id}


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "UnityGrid AI backend",
        "docs": "/docs",
        "health": "/health",
    }
