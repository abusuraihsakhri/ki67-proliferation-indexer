#!/usr/bin/env python3
"""
Ki-67 Proliferation Indexer
Calculates Ki-67 labeling index (%) from hot-spot and global counts with breast/NET grading cutoffs.

Zero-dependency Python implementation with single and batch evaluation.
Author: Dr. Abu Suraih Sakhri
License: MIT
"""

import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Dict, Any, List, Optional


def calculate_index(positive_cells: int, total_cells: int) -> Dict[str, Any]:
    """Ki-67 labeling index = 100 * positive tumour nuclei / total tumour nuclei.

    Counts must be non-negative integers, with a nonzero denominator and no more
    positive than total nuclei. This arithmetic does not establish tumour grade.
    """
    for name, value in (("positive_cells", positive_cells), ("total_cells", total_cells)):
        if isinstance(value, bool) or not str(value).strip().isdigit():
            raise ValueError(f"{name} must be a non-negative integer.")
    positive, total = int(positive_cells), int(total_cells)
    if total == 0:
        raise ValueError("total_cells must be greater than zero.")
    if positive > total:
        raise ValueError("positive_cells cannot exceed total_cells.")
    return {
        "tool": "ki67-proliferation-indexer",
        "score": round(100.0 * positive / total, 2),
        "positive_cells": positive,
        "total_cells": total,
        "method": "positive_over_total",
        "classification": "Not assigned; tumour-specific interpretation required",
        "clinical_recommendation": "None. Validate counting method and interpret in the appropriate tumour context.",
        "inputs_evaluated": 2,
    }


def calculate_metrics(**kwargs) -> Dict[str, Any]:
    """Compute a count-based Ki-67 index, or preserve explicitly labeled legacy scores.

    Prefer positive_cells and total_cells. Legacy v1, v2, ... weighted sums are
    retained solely for backwards compatibility and are NOT labeling indices.
    """
    has_positive = kwargs.get("positive_cells") is not None
    has_total = kwargs.get("total_cells") is not None
    if has_positive or has_total:
        if not (has_positive and has_total):
            raise ValueError("Both positive_cells and total_cells are required.")
        return calculate_index(kwargs["positive_cells"], kwargs["total_cells"])

    numeric = []
    params = {}
    for key, value in kwargs.items():
        if value is None:
            continue
        if not re.fullmatch(r"v[1-9][0-9]*", key):
            params[key] = str(value)
            continue
        try:
            fv = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{key} must be a finite numeric percentage.") from exc
        if not math.isfinite(fv):
            raise ValueError(f"{key} must be finite.")
        if not (0 <= fv <= 100):
            raise ValueError(f"Parameter '{key}' value {fv} is outside valid Ki-67 range [0, 100].")
        params[key] = fv
        numeric.append(fv)
    if not numeric:
        raise ValueError("Provide positive_cells and total_cells, or legacy v1/v2/... values.")
    score = sum(value / index for index, value in enumerate(numeric, 1))
    rounded_score = round(score, 2)
    if rounded_score < 10:
        tier = "Low / Standard"
    elif rounded_score < 25:
        tier = "Moderate / Intermediate"
    else:
        tier = "High / Severe"
    return {
        "tool": "ki67-proliferation-indexer",
        "score": rounded_score,
        "classification": tier,
        "method": "legacy_weighted_proxy_not_ki67",
        "warning": "Legacy weighted proxy: not a valid Ki-67 labeling index or clinical grade.",
        "clinical_recommendation": "None; do not use the legacy score for clinical decisions.",
        "inputs_evaluated": len(params),
    }


def process_single(args) -> None:
    """
    Process a single case from CLI arguments.

    Args:
        args: Parsed argparse namespace containing v1, v2, v3 parameters.
    """
    kwargs = vars(args).copy()
    kwargs.pop("func", None)
    kwargs.pop("command", None)
    res = calculate_metrics(**kwargs)
    print(json.dumps(res, indent=2))


def process_batch(input_csv: str, output_csv: str) -> None:
    """
    Process a batch of cases from an input CSV file.

    Reads patient records from input_csv, computes Ki-67 scores for each,
    and writes results to output_csv with additional score columns.

    Args:
        input_csv: Path to the input CSV file containing patient records.
        output_csv: Path where the output CSV with scores will be written.

    Raises:
        FileNotFoundError: If input_csv does not exist.
        ValueError: If the CSV is empty or has no valid headers.
        csv.Error: If the CSV file is malformed.
    """
    input_path = Path(input_csv)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_csv}")
    if not input_path.is_file():
        raise ValueError(f"Input path is not a file: {input_csv}")
    if input_path.stat().st_size == 0:
        raise ValueError(f"Input file is empty: {input_csv}")

    try:
        with open(input_csv, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames or [])
            if not fieldnames:
                raise ValueError(f"CSV file has no headers or is malformed: {input_csv}")
            rows = list(reader)
    except csv.Error as e:
        raise ValueError(f"Failed to parse CSV file {input_csv}: {e}") from e

    if ("positive_cells" in fieldnames) != ("total_cells" in fieldnames):
        raise ValueError("CSV requires both positive_cells and total_cells.")
    if not {"positive_cells", "total_cells"}.issubset(fieldnames) and not any(
        re.fullmatch(r"v[1-9][0-9]*", name) for name in fieldnames
    ):
        raise ValueError("CSV requires counts or legacy v1/v2/... columns.")
    if any(None in row for row in rows):
        raise ValueError("CSV contains more values than declared headers.")

    added = ["score", "classification", "clinical_recommendation", "method"]
    out_fields = list(dict.fromkeys(fieldnames + added))
    out_rows = []

    for r in rows:
        if "positive_cells" in fieldnames:
            calc_res = calculate_metrics(
                positive_cells=r["positive_cells"], total_cells=r["total_cells"]
            )
        else:
            values = {
                key: value for key, value in r.items()
                if re.fullmatch(r"v[1-9][0-9]*", key) and value not in ("", None)
            }
            calc_res = calculate_metrics(**values)
        row_dict = dict(r)
        row_dict["score"] = calc_res["score"]
        row_dict["classification"] = calc_res["classification"]
        row_dict["clinical_recommendation"] = calc_res["clinical_recommendation"]
        row_dict["method"] = calc_res["method"]
        out_rows.append(row_dict)

    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"Processed {len(out_rows)} records -> {output_csv}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Ki-67 Proliferation Indexer - Calculate Ki-67 labeling index from cell counts."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Single parser
    single_parser = subparsers.add_parser("single", help="Evaluate single case")
    single_parser.add_argument(
        "--v1", type=float, default=10.0,
        help="Primary Ki-67 value (%% positive cells, 0-100)"
    )
    single_parser.add_argument(
        "--v2", type=float, default=5.0,
        help="Secondary Ki-67 value (%% positive cells, 0-100)"
    )
    single_parser.add_argument(
        "--v3", type=float, default=2.0,
        help="Tertiary Ki-67 value (%% positive cells, 0-100)"
    )
    single_parser.add_argument("--positive-cells", type=int, default=None, help="Ki-67 positive tumour nuclei")
    single_parser.add_argument("--total-cells", type=int, default=None, help="All tumour nuclei counted")
    single_parser.set_defaults(func=process_single)

    # Batch parser
    batch_parser = subparsers.add_parser("batch", help="Process batch CSV")
    batch_parser.add_argument(
        "-i", "--input", required=True,
        help="Input CSV file with patient records"
    )
    batch_parser.add_argument(
        "-o", "--output", default="results.csv",
        help="Output CSV file path (default: results.csv)"
    )

    args = parser.parse_args(argv)

    if args.command == "single":
        args.func(args)
    elif args.command == "batch":
        process_batch(args.input, args.output)


if __name__ == "__main__":
    main()
