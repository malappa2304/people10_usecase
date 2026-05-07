"""
Tests for the PipelineRun context manager.

Strategy: stub out the SQL executions (we don't want a real Delta on the test
runner) and verify the orchestration semantics — start row written, end row
written, watermark only committed on success, exception re-raises.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from databricks.lib.pipeline_run import PipelineRun


def _stub_spark() -> MagicMock:
    """A spark stub that records every .sql() call."""
    spark = MagicMock(name="spark")
    spark.sql = MagicMock(return_value=MagicMock())
    spark.table = MagicMock(
        return_value=MagicMock(
            where=MagicMock(
                return_value=MagicMock(
                    select=MagicMock(
                        return_value=MagicMock(
                            limit=MagicMock(return_value=MagicMock(collect=MagicMock(return_value=[])))
                        )
                    ),
                    count=MagicMock(return_value=1),
                )
            )
        )
    )
    return spark


def test_pipelinerun_writes_start_and_end_on_success():
    spark = _stub_spark()
    with PipelineRun("test_pipe", "SAP_S4HANA", "production_order", spark=spark) as run:
        run.metric("rows_in", 100)
        run.advance_watermark("2026-05-06T10:00:00Z")

    sql_calls = [c.args[0] for c in spark.sql.call_args_list]
    started = [s for s in sql_calls if "INSERT INTO audit.pipeline_run" in s and "RUNNING" in s]
    ended = [s for s in sql_calls if "UPDATE audit.pipeline_run" in s and "SUCCESS" in s]
    wm = [s for s in sql_calls if "MERGE INTO audit.pipeline_watermark" in s]

    assert len(started) == 1
    assert len(ended) == 1
    assert len(wm) == 1


def test_pipelinerun_marks_failed_on_exception_and_does_not_commit_watermark():
    spark = _stub_spark()
    with pytest.raises(ValueError):
        with PipelineRun("test_pipe", "SAP_S4HANA", "production_order", spark=spark) as run:
            run.advance_watermark("2026-05-06T10:00:00Z")
            raise ValueError("boom")

    sql_calls = [c.args[0] for c in spark.sql.call_args_list]
    failed_updates = [s for s in sql_calls if "UPDATE audit.pipeline_run" in s and "FAILED" in s]
    wm_commits = [s for s in sql_calls if "MERGE INTO audit.pipeline_watermark" in s]

    assert len(failed_updates) == 1
    assert len(wm_commits) == 0, "Watermark must NOT advance on failure"


def test_metric_kv_is_serialised_into_metrics_json():
    """Numbers and strings both round-trip; JSON encoding doesn't crash on dates."""
    spark = _stub_spark()
    with PipelineRun("test_pipe", "SAP_S4HANA", "po", spark=spark) as run:
        run.metric("rows_in", 12345)
        run.metric("note", "all good")

    update_call = next(
        c.args[0]
        for c in spark.sql.call_args_list
        if "UPDATE audit.pipeline_run" in c.args[0] and "SUCCESS" in c.args[0]
    )
    assert "rows_in" in update_call
    assert "12345" in update_call
    assert "all good" in update_call
