"""Regression tests for count-based Ki-67 arithmetic and audit authentication."""
import csv

import pytest
from ki67_indexer import calculate_index, calculate_metrics, process_batch
from agents.base import AuditTrail
from agents.api import app
from fastapi.testclient import TestClient


def test_count_based_ratio_and_boundary_values():
    assert calculate_index(125, 500)["score"] == 25.0
    assert calculate_index(0, 500)["score"] == 0
    assert calculate_index(500, 500)["score"] == 100
    result = calculate_metrics(positive_cells="50", total_cells="200")
    assert result["method"] == "positive_over_total"
    assert result["score"] == 25.0
    assert "Not assigned" in result["classification"]


@pytest.mark.parametrize("positive,total", [
    (-1, 10), (1, 0), (11, 10), (1.5, 10),
    (True, 10), ("NaN", 10), (1, None), (1, -10)
])
def test_invalid_counts_rejected(positive, total):
    with pytest.raises(ValueError):
        calculate_index(positive, total)


def test_partial_count_pair_rejected():
    with pytest.raises(ValueError, match="Both"):
        calculate_metrics(positive_cells=2)


def test_legacy_proxy_is_explicit_and_nonclinical():
    result = calculate_metrics(v1=10, v2=6)
    assert result["score"] == 13
    assert result["method"] == "legacy_weighted_proxy_not_ki67"
    assert "not a valid Ki-67" in result["warning"]
    with pytest.raises(ValueError):
        calculate_metrics(v1=float("nan"))
    with pytest.raises(ValueError):
        calculate_metrics(v1=float("inf"))
    with pytest.raises(ValueError):
        calculate_metrics(sample_id="S1")


def test_batch_counts_ignore_numeric_metadata(tmp_path):
    source = tmp_path / "counts.csv"
    output = tmp_path / "out.csv"
    source.write_text(
        "sample_id,positive_cells,total_cells,numeric_mrn\n"
        "S1,50,200,999999\nS2,0,100,123456\n", encoding="utf-8"
    )
    process_batch(str(source), str(output))
    with output.open(newline="", encoding="utf-8") as f:
        data = list(csv.DictReader(f))
    assert [row["score"] for row in data] == ["25.0", "0.0"]
    assert all(row["method"] == "positive_over_total" for row in data)


def test_batch_rejects_partial_schema(tmp_path):
    source = tmp_path / "bad.csv"
    source.write_text("positive_cells,sample\n10,A\n", encoding="utf-8")
    with pytest.raises(ValueError, match="both"):
        process_batch(str(source), str(tmp_path / "out.csv"))


def test_hmac_verification_detects_field_change():
    trail = AuditTrail(secret_key="a-dedicated-test-only-key-of-sufficient-length")
    trail.log("test", "test", "CREATE", {"ok": True})
    trail.log("test", "test", "COMPLETE", {"ok": True})
    assert trail.verify_integrity()
    copied = trail.get_trail()
    copied[0]["actor"] = "external"
    assert trail.verify_integrity()
    trail.logs[0]["actor"] = "changed"
    assert not trail.verify_integrity()


def test_count_api_validation_and_static_root():
    client = TestClient(app)
    response = client.post("/api/ki67", json={"positive_cells": 25, "total_cells": 100})
    assert response.status_code == 200
    assert response.json()["score"] == 25
    assert client.post("/api/ki67", json={"positive_cells": 101, "total_cells": 100}).status_code == 422
    assert client.post("/api/ki67", json={"positive_cells": 1.2, "total_cells": 100}).status_code == 422
    root = client.get("/")
    assert root.status_code == 200
    assert "Positive tumour nuclei" in root.text


def test_hmac_field_delimiter_transfer_is_detected():
    trail = AuditTrail(secret_key="a-dedicated-test-only-key-of-sufficient-length")
    trail.log("actor|tier", "role", "EVENT", {"ok": True})
    assert trail.verify_integrity()
    trail.logs[0]["actor"] = "actor"
    trail.logs[0]["actor_tier"] = "tier|role"
    assert not trail.verify_integrity()


def test_batch_refuses_overwrite_source_file(tmp_path):
    source = tmp_path / "counts.csv"
    source.write_text("positive_cells,total_cells\n1,10\n", encoding="utf-8")
    with pytest.raises(ValueError, match="different"):
        process_batch(str(source), str(source))
    assert "1,10" in source.read_text(encoding="utf-8")


def test_legacy_column_order_not_reinterpreted(tmp_path):
    source = tmp_path / "legacy.csv"
    result = tmp_path / "legacy_out.csv"
    source.write_text("v2,v1\n6,10\n", encoding="utf-8")
    process_batch(str(source), str(result))
    with result.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    assert float(row["score"]) == 13.0
