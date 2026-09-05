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
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional


def calculate_metrics(**kwargs) -> Dict[str, Any]:
    """
    Core domain algorithm for ki67-proliferation-indexer.

    Computes a Ki-67 proliferation score from one or more numeric input values.
    The primary value contributes fully; subsequent values contribute with
    diminishing weights (1/n).

    Args:
        **kwargs: Named numeric parameters (v1, v2, v3, ...). Non-numeric
                  values are treated as metadata and excluded from scoring.

    Returns:
        Dictionary with score, classification, clinical recommendation, and
        metadata about the computation.

    Raises:
        ValueError: If any numeric value is outside the valid Ki-67 range [0, 100].
    """
    params = {}
    for k, v in kwargs.items():
        if v is not None:
            try:
                fv = float(v)
                # Ki-67 values represent percentages and must be in [0, 100]
                if fv < 0.0 or fv > 100.0:
                    raise ValueError(
                        f"Parameter '{k}' value {fv} is outside valid Ki-67 range [0, 100]."
                    )
                params[k] = fv
            except (ValueError, TypeError) as e:
                if "outside valid Ki-67 range" in str(e):
                    raise
                params[k] = str(v)

    # Deterministic domain logic
    numeric_vals = [val for val in params.values() if isinstance(val, (int, float))]
    primary_val = numeric_vals[0] if numeric_vals else 0.0

    score = primary_val
    for idx, nv in enumerate(numeric_vals[1:], start=2):
        score += nv * (1.0 / idx)

    rounded_score = round(score, 2)

    # Classification / tiering based on standard Ki-67 cutoffs
    # Low: <10% (grade 1), Moderate: 10-25% (grade 2), High: >25% (grade 3)
    if rounded_score < 10.0:
        tier = "Low / Standard"
        action = "Standard monitoring or negative cutoff"
    elif rounded_score < 25.0:
        tier = "Moderate / Intermediate"
        action = "Close observation or secondary evaluation"
    else:
        tier = "High / Severe"
        action = "Urgent clinical intervention or primary positive finding"

    return {
        "tool": "ki67-proliferation-indexer",
        "score": rounded_score,
        "classification": tier,
        "clinical_recommendation": action,
        "inputs_evaluated": len(params),
    }


def process_single(args) -> None:
    """
    Process a single case from CLI arguments.

    Args:
        args: Parsed argparse namespace containing v1, v2, v3 parameters.
    """
    kwargs = vars(args)
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

    out_fields = fieldnames + ["score", "classification", "clinical_recommendation"]
    out_rows = []

    for r in rows:
        calc_res = calculate_metrics(**r)
        row_dict = dict(r)
        row_dict["score"] = calc_res["score"]
        row_dict["classification"] = calc_res["classification"]
        row_dict["clinical_recommendation"] = calc_res["clinical_recommendation"]
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
