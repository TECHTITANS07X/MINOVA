from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import psycopg2
import psycopg2.extras
import structlog
from temporalio import activity

logger = structlog.get_logger()

DB_DSN = "postgresql://minova_app:minova_dev@localhost:5433/minova"

psycopg2.extras.register_uuid()


def _conn():
    return psycopg2.connect(DB_DSN)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class _DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, (datetime,)):
            return o.isoformat()
        if isinstance(o, uuid.UUID):
            return str(o)
        return super().default(o)


def _json_dumps(obj) -> str:
    return json.dumps(obj, cls=_DecimalEncoder)


@activity.defn
async def fetch_shift_entries(mine_id: str, date: str) -> list[dict]:
    with _conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT se.id, se.mine_id, se.bench_id, se.shift_date, se.shift_number,
                   se.status, se.submitted_by, se.created_at,
                   json_agg(json_build_object(
                       'metric', ev.metric_name, 'value', ev.value, 'unit', ev.unit
                   )) AS values
            FROM shift_entry se
            LEFT JOIN entry_value ev ON ev.entry_id = se.id
            WHERE se.mine_id = %s AND se.shift_date = %s
            GROUP BY se.id
            ORDER BY se.shift_number
            """,
            (mine_id, date),
        )
        rows = cur.fetchall()
    return [dict(r) for r in rows]


@activity.defn
async def fetch_approved_entries(mine_id: str, date: str) -> list[dict]:
    with _conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT se.id, se.shift_number,
                   json_agg(json_build_object(
                       'metric', ev.metric_name, 'value', ev.value::text, 'unit', ev.unit
                   )) AS values
            FROM shift_entry se
            LEFT JOIN entry_value ev ON ev.entry_id = se.id
            WHERE se.mine_id = %s AND se.shift_date = %s AND se.status = 'approved'
            GROUP BY se.id, se.shift_number
            ORDER BY se.shift_number
            """,
            (mine_id, date),
        )
        rows = cur.fetchall()
    return [dict(r) for r in rows]


@activity.defn
async def run_calculation(calc_type: str, input_data: dict) -> dict:
    from app.services.calculation import (
        aggregate_shifts_to_daily,
        aggregate_period,
        compute_stripping_ratio,
        compute_target_vs_actual,
        CalcRunRecord,
        ShiftRecord,
    )

    if calc_type == "aggregate_shifts_to_daily":
        shifts = [
            ShiftRecord(
                shift_number=s["shift_number"],
                metric=s["metric"],
                value=Decimal(str(s["value"])),
                unit=s.get("unit", "t"),
            )
            for s in input_data["shifts"]
        ]
        result = aggregate_shifts_to_daily(shifts)
        return {
            "totals": {k: str(v) for k, v in result.totals.items()},
            "input_hash": result.input_hash,
            "formula_version": result.formula_version,
        }

    if calc_type == "stripping_ratio":
        ob = Decimal(str(input_data["overburden"]))
        coal = Decimal(str(input_data["coal"]))
        ratio = compute_stripping_ratio(ob, coal)
        return {"ratio": str(ratio)}

    if calc_type == "target_vs_actual":
        target = Decimal(str(input_data["target"]))
        actual = Decimal(str(input_data["actual"]))
        result = compute_target_vs_actual(target, actual)
        return {k: str(v) for k, v in result.items()}

    raise ValueError(f"Unknown calc_type: {calc_type}")


@activity.defn
async def create_audit_event(
    action: str,
    entity_type: str,
    entity_id: str,
    user_id: str,
    details: dict,
) -> None:
    now = _utcnow()
    event_id = str(uuid.uuid4())
    details_json = _json_dumps(details)

    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT prev_hash FROM audit_event ORDER BY created_at DESC LIMIT 1"
        )
        row = cur.fetchone()
        prev_hash = row[0] if row else "GENESIS"

        payload = f"{prev_hash}|{action}|{entity_type}|{entity_id}|{user_id}|{now.isoformat()}"
        current_hash = hashlib.sha256(payload.encode()).hexdigest()

        cur.execute(
            """
            INSERT INTO audit_event (id, action, entity_type, entity_id, user_id,
                                     details, prev_hash, hash, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (event_id, action, entity_type, entity_id, user_id,
             details_json, prev_hash, current_hash, now),
        )
        conn.commit()
    logger.info("audit.created", action=action, entity=f"{entity_type}:{entity_id}")


@activity.defn
async def send_notification(user_id: str, title: str, body: str) -> None:
    logger.info("notification.sent", user_id=user_id, title=title, body=body[:100])


@activity.defn
async def check_anomalies(mine_id: str, metric: str, value: float) -> list[dict]:
    with _conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT ev.value::float AS val
            FROM entry_value ev
            JOIN shift_entry se ON se.id = ev.entry_id
            WHERE se.mine_id = %s AND ev.metric_name = %s AND se.status = 'approved'
            ORDER BY se.shift_date DESC
            LIMIT 90
            """,
            (mine_id, metric),
        )
        history = [r["val"] for r in cur.fetchall()]

    if len(history) < 10:
        return []

    try:
        import numpy as np
        from sklearn.ensemble import IsolationForest

        data = np.array(history + [value]).reshape(-1, 1)
        clf = IsolationForest(contamination=0.05, random_state=42)
        preds = clf.fit_predict(data)
        if preds[-1] == -1:
            mean_val = float(np.mean(history))
            std_val = float(np.std(history))
            deviation = abs(value - mean_val) / std_val if std_val > 0 else 0
            return [{
                "mine_id": mine_id,
                "metric": metric,
                "value": value,
                "mean": mean_val,
                "std": std_val,
                "deviation_sigma": round(deviation, 2),
                "severity": "high" if deviation > 3 else "medium",
            }]
    except ImportError:
        logger.warning("anomaly.sklearn_unavailable")

    return []


@activity.defn
async def store_calc_run(run_record: dict) -> str:
    run_id = str(uuid.uuid4())
    now = _utcnow()
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO calc_run (id, calc_type, input_hash, formula_version,
                                  inputs_json, outputs_json, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                run_id,
                run_record.get("calc_type", "rollup"),
                run_record.get("input_hash", ""),
                run_record.get("formula_version", "1.0"),
                _json_dumps(run_record.get("inputs", {})),
                _json_dumps(run_record.get("outputs", {})),
                now,
            ),
        )
        conn.commit()
    return run_id


@activity.defn
async def update_entry_status(entry_id: str, status: str) -> None:
    now = _utcnow()
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE shift_entry SET status = %s, updated_at = %s WHERE id = %s",
            (status, now, entry_id),
        )
        conn.commit()
    logger.info("entry.status_updated", entry_id=entry_id, status=status)


@activity.defn
async def create_conflict_flag(entry_id: str, details: dict) -> str:
    flag_id = str(uuid.uuid4())
    now = _utcnow()
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO conflict_flag (id, entity_type, entity_id, metric,
                                       value_a, source_a, value_b, source_b,
                                       resolution, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                flag_id,
                details.get("entity_type", "shift_entry"),
                entry_id,
                details.get("metric", ""),
                details.get("value_a", 0),
                details.get("source_a", ""),
                details.get("value_b", 0),
                details.get("source_b", ""),
                "unresolved",
                now,
            ),
        )
        conn.commit()
    return flag_id


@activity.defn
async def get_approval_chain(mine_id: str) -> list[dict]:
    with _conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT al.id, al.level_number, al.role_name, al.sla_hours
            FROM approval_level al
            JOIN approval_chain ac ON ac.id = al.chain_id
            WHERE ac.mine_id = %s AND ac.is_active = true
            ORDER BY al.level_number
            """,
            (mine_id,),
        )
        return [dict(r) for r in cur.fetchall()]


@activity.defn
async def create_approval_task(
    entry_id: str, level_id: str, level_number: int, role_name: str
) -> str:
    task_id = str(uuid.uuid4())
    now = _utcnow()
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO approval_task (id, entry_id, level_id, level_number,
                                       role_name, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (task_id, entry_id, level_id, level_number, role_name, "pending", now),
        )
        conn.commit()
    return task_id


@activity.defn
async def complete_approval_task(task_id: str, action: str, user_id: str, comment: str) -> None:
    now = _utcnow()
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE approval_task SET status = %s, decided_by = %s,
                   decision_comment = %s, decided_at = %s
            WHERE id = %s
            """,
            (action, user_id, comment, now, task_id),
        )
        conn.commit()


@activity.defn
async def store_report_values(mine_id: str, date: str, period: str, values: dict) -> str:
    report_id = str(uuid.uuid4())
    now = _utcnow()
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO report (id, mine_id, period, start_date, end_date, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (report_id, mine_id, period, date, date, "generated", now),
        )
        for metric, val in values.items():
            rv_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO report_value (id, report_id, metric_name, value, unit, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (rv_id, report_id, metric, Decimal(str(val)), "t", now),
            )
        conn.commit()
    return report_id


@activity.defn
async def create_anomaly_flag(mine_id: str, anomaly: dict) -> str:
    flag_id = str(uuid.uuid4())
    now = _utcnow()
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO anomaly_flag (id, mine_id, metric, value, expected_range_low,
                                      expected_range_high, severity, status, details, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                flag_id,
                mine_id,
                anomaly["metric"],
                anomaly["value"],
                anomaly["mean"] - 2 * anomaly["std"],
                anomaly["mean"] + 2 * anomaly["std"],
                anomaly.get("severity", "medium"),
                "open",
                _json_dumps(anomaly),
                now,
            ),
        )
        conn.commit()
    return flag_id


@activity.defn
async def download_document(document_id: str) -> dict:
    with _conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT id, storage_key, content_type, filename FROM document WHERE id = %s",
            (document_id,),
        )
        row = cur.fetchone()
    if not row:
        raise ValueError(f"Document {document_id} not found")
    return dict(row)


@activity.defn
async def run_ocr(storage_key: str, language: str = "en+hi") -> list[dict]:
    logger.info("ocr.processing", key=storage_key, language=language)
    return [{"page": 1, "text": "(OCR placeholder — PaddleOCR not yet wired)", "tables": []}]


@activity.defn
async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    logger.info("embeddings.generating", count=len(texts))
    return [[0.0] * 1024 for _ in texts]


@activity.defn
async def store_doc_chunks(document_id: str, chunks: list[dict]) -> int:
    now = _utcnow()
    with _conn() as conn, conn.cursor() as cur:
        for i, chunk in enumerate(chunks):
            chunk_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO doc_chunk (id, document_id, page_number, chunk_index,
                                       text, embedding, metadata_json, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    chunk_id,
                    document_id,
                    chunk.get("page", 1),
                    i,
                    chunk["text"],
                    _json_dumps(chunk.get("embedding")),
                    _json_dumps(chunk.get("metadata", {})),
                    now,
                ),
            )
        conn.commit()
    return len(chunks)


@activity.defn
async def update_document_status(document_id: str, status: str) -> None:
    now = _utcnow()
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE document SET ingestion_status = %s, updated_at = %s WHERE id = %s",
            (status, now, document_id),
        )
        conn.commit()


@activity.defn
async def store_extracted_tables(document_id: str, tables: list[dict]) -> int:
    now = _utcnow()
    count = 0
    with _conn() as conn, conn.cursor() as cur:
        for tbl in tables:
            tbl_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO extracted_table (id, document_id, page_number, table_index,
                                             headers, rows_json, confidence, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    tbl_id,
                    document_id,
                    tbl.get("page", 1),
                    tbl.get("index", 0),
                    _json_dumps(tbl.get("headers", [])),
                    _json_dumps(tbl.get("rows", [])),
                    tbl.get("confidence", 0.0),
                    now,
                ),
            )
            count += 1
        conn.commit()
    return count


ALL_ACTIVITIES = [
    fetch_shift_entries,
    fetch_approved_entries,
    run_calculation,
    create_audit_event,
    send_notification,
    check_anomalies,
    store_calc_run,
    update_entry_status,
    create_conflict_flag,
    get_approval_chain,
    create_approval_task,
    complete_approval_task,
    store_report_values,
    create_anomaly_flag,
    download_document,
    run_ocr,
    generate_embeddings,
    store_doc_chunks,
    update_document_status,
    store_extracted_tables,
]
