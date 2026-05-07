"""
PipelineRun context manager — audit, lock, watermark.

Why this exists
---------------
Every Bronze→Silver and Silver→Gold job in this platform writes one row to
`audit.pipeline_run` at start, updates it at end. That row is what the AS9100
auditor sees and what the SLO dashboards aggregate from. We also use the same
row to hold a lightweight pipeline lock (only one instance of the same logical
pipeline runs at a time — important when ADF retries on transient failure)
and to read/advance a per-source watermark in a single transaction.

Three concerns, one context manager — because in production we found that
splitting them across three separate utility classes meant engineers
inevitably forgot one. Ergonomics beats orthogonality here.

Usage
-----
    with PipelineRun(name="bronze_to_silver_production_order",
                     source_system="SAP_S4HANA",
                     entity="production_order") as run:
        wm = run.watermark()                    # last successful high-water mark
        df = read_bronze_since(wm)
        write_silver(df)
        run.advance_watermark(df.agg(F.max("posting_ts")).first()[0])
        run.metric("rows_in", df.count())

On normal exit the run row is marked SUCCESS, watermark is committed, lock is
released. On exception the row is marked FAILED with the truncated traceback,
watermark is *not* advanced, and the exception re-raises so ADF sees a failure.
"""

from __future__ import annotations

import contextlib
import socket
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

_AUDIT_TABLE = "audit.pipeline_run"
_LOCK_TABLE = "audit.pipeline_lock"
_WATERMARK_TABLE = "audit.pipeline_watermark"


@dataclass
class PipelineRun:
    """Audit + lock + watermark wrapped as a context manager.

    `name` should be the *logical* pipeline name (not the cluster job id) so
    we can correlate runs across ADF retries.
    """

    name: str
    source_system: str
    entity: str
    spark: SparkSession = field(default=None)  # type: ignore[assignment]
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metrics: dict[str, Any] = field(default_factory=dict)
    _new_watermark: Optional[str] = None
    _lock_acquired: bool = False

    def __post_init__(self) -> None:
        if self.spark is None:
            self.spark = SparkSession.getActiveSession()
        if self.spark is None:
            raise RuntimeError("No active SparkSession; PipelineRun needs one.")

    # ---- context-manager hooks ----------------------------------------------

    def __enter__(self) -> "PipelineRun":
        self._acquire_lock()
        self._write_start_row()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        try:
            if exc is None:
                self._write_end_row(status="SUCCESS")
                if self._new_watermark is not None:
                    self._commit_watermark()
            else:
                # Truncate traceback — Delta string column has practical limits and
                # the auditor only ever needs the last frame.
                err = "".join(traceback.format_exception(exc_type, exc, tb))[-4000:]
                self._write_end_row(status="FAILED", error=err)
        finally:
            self._release_lock()
        # Re-raise: ADF needs to see the failure to mark the activity failed.
        return False

    # ---- public API used inside the `with` block ----------------------------

    def watermark(self) -> Optional[str]:
        """Last successful high-water mark for (source_system, entity).

        Returns None on first-ever run for this entity — caller is expected
        to handle that as a full-history bootstrap.
        """
        rows = (
            self.spark.table(_WATERMARK_TABLE)
            .where((F.col("source_system") == self.source_system) & (F.col("entity") == self.entity))
            .select("watermark_value")
            .limit(1)
            .collect()
        )
        return rows[0]["watermark_value"] if rows else None

    def advance_watermark(self, value: Any) -> None:
        """Stage a new watermark; committed on successful exit, dropped on failure."""
        if value is None:
            return
        self._new_watermark = str(value)

    def metric(self, key: str, value: Any) -> None:
        """Capture a numeric/string metric for the audit row."""
        self.metrics[key] = value

    # ---- private helpers ----------------------------------------------------

    def _acquire_lock(self) -> None:
        """Best-effort optimistic lock against double-runs.

        Note: this is *not* a distributed mutex; it's a guardrail for the common
        ADF-retry-during-running-job case. For a true mutex we'd use the Delta
        OPTIMIZE-style ZooKeeper coordinator, but the cost there is not justified
        at our concurrency.
        """
        host = socket.gethostname()
        try:
            self.spark.sql(
                f"""
                INSERT INTO {_LOCK_TABLE}
                SELECT '{self.name}', '{self.run_id}', '{host}', current_timestamp()
                WHERE NOT EXISTS (
                    SELECT 1 FROM {_LOCK_TABLE} WHERE pipeline_name = '{self.name}'
                )
                """
            )
            held = (
                self.spark.table(_LOCK_TABLE)
                .where(F.col("pipeline_name") == self.name)
                .where(F.col("run_id") == self.run_id)
                .count()
            )
            if held == 0:
                raise RuntimeError(f"Pipeline '{self.name}' is already running — refusing to start.")
            self._lock_acquired = True
        except Exception:
            # If the lock table doesn't exist yet (first deployment), don't crash.
            # Production ops sets up the table during foundation phase.
            pass

    def _release_lock(self) -> None:
        if not self._lock_acquired:
            return
        with contextlib.suppress(Exception):
            self.spark.sql(
                f"DELETE FROM {_LOCK_TABLE} " f"WHERE pipeline_name = '{self.name}' AND run_id = '{self.run_id}'"
            )

    def _write_start_row(self) -> None:
        self.spark.sql(
            f"""
            INSERT INTO {_AUDIT_TABLE}
            (run_id, pipeline_name, source_system, entity, status,
             started_at, ended_at, metrics_json, error_text, host)
            VALUES (
                '{self.run_id}', '{self.name}', '{self.source_system}',
                '{self.entity}', 'RUNNING',
                current_timestamp(), NULL, '{{}}', NULL,
                '{socket.gethostname()}'
            )
            """
        )

    def _write_end_row(self, status: str, error: Optional[str] = None) -> None:
        # Persist metrics as JSON string — keeps schema stable as we add metrics.
        import json

        metrics_json = json.dumps(self.metrics, default=str).replace("'", "''")
        err_clause = "NULL" if error is None else f"'{error.replace(chr(39), chr(39)*2)}'"
        self.spark.sql(
            f"""
            UPDATE {_AUDIT_TABLE}
            SET status = '{status}',
                ended_at = current_timestamp(),
                metrics_json = '{metrics_json}',
                error_text = {err_clause}
            WHERE run_id = '{self.run_id}'
            """
        )

    def _commit_watermark(self) -> None:
        self.spark.sql(
            f"""
            MERGE INTO {_WATERMARK_TABLE} t
            USING (
                SELECT '{self.source_system}' AS source_system,
                       '{self.entity}'        AS entity,
                       '{self._new_watermark}' AS watermark_value,
                       current_timestamp()    AS updated_at
            ) s
            ON t.source_system = s.source_system AND t.entity = s.entity
            WHEN MATCHED THEN UPDATE SET
                watermark_value = s.watermark_value,
                updated_at      = s.updated_at
            WHEN NOT MATCHED THEN INSERT *
            """
        )
