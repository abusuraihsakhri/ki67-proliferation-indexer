import pytest
from ki67_indexer import calculate_metrics, process_batch, main


def test_ki67_indexer_single():
    res = calculate_metrics(v1=12.0, v2=4.0)
    assert "score" in res
    assert "classification" in res
    assert res["score"] > 0


def test_ki67_indexer_batch(tmp_path):
    csv_in = tmp_path / "in.csv"
    csv_out = tmp_path / "out.csv"
    csv_in.write_text("Patient,v1,v2\nPat_001,15.0,3.0\nPat_002,5.0,1.0\n", encoding="utf-8")

    process_batch(str(csv_in), str(csv_out))
    assert csv_out.exists()
    content = csv_out.read_text(encoding="utf-8")
    assert "Pat_001" in content
    assert "score" in content


def test_ki67_classification_low():
    """Values below 10% should classify as Low/Standard."""
    res = calculate_metrics(v1=5.0)
    assert res["classification"] == "Low / Standard"
    assert res["score"] == 5.0


def test_ki67_classification_moderate():
    """Values between 10-25% should classify as Moderate/Intermediate."""
    res = calculate_metrics(v1=15.0)
    assert res["classification"] == "Moderate / Intermediate"


def test_ki67_classification_high():
    """Values above 25% should classify as High/Severe."""
    res = calculate_metrics(v1=30.0)
    assert res["classification"] == "High / Severe"


def test_ki67_weighted_calculation():
    """Score should be v1 + v2/2 + v3/3."""
    res = calculate_metrics(v1=10.0, v2=6.0, v3=9.0)
    expected = 10.0 + 6.0/2 + 9.0/3  # = 10 + 3 + 3 = 16.0
    assert res["score"] == round(expected, 2)


def test_ki67_invalid_range_rejected():
    """Values outside [0, 100] should raise ValueError."""
    with pytest.raises(ValueError, match="outside valid Ki-67 range"):
        calculate_metrics(v1=-5.0)
    with pytest.raises(ValueError, match="outside valid Ki-67 range"):
        calculate_metrics(v1=150.0)


def test_ki67_batch_file_not_found():
    """process_batch should raise FileNotFoundError for missing input."""
    with pytest.raises(FileNotFoundError):
        process_batch("nonexistent_file.csv", "output.csv")


def test_ki67_batch_empty_file(tmp_path):
    """process_batch should raise ValueError for empty CSV."""
    csv_in = tmp_path / "empty.csv"
    csv_in.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        process_batch(str(csv_in), str(tmp_path / "out.csv"))


def test_ki67_cli_single():
    """CLI single command should work."""
    result = main(["single", "--v1", "15.0"])
    assert result is None  # main() returns None for single


def test_ki67_cli_batch(tmp_path, capsys):
    """CLI batch command should process CSV."""
    csv_in = tmp_path / "in.csv"
    csv_out = tmp_path / "out.csv"
    csv_in.write_text("Patient,v1\nPat_001,15.0\n", encoding="utf-8")
    main(["batch", "-i", str(csv_in), "-o", str(csv_out)])
    assert csv_out.exists()
