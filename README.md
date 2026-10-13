# Ki-67 Proliferation Indexer

Calculate the **Ki-67 labeling index from cell counts**: the percentage of eligible tumour nuclei that stain positive for Ki-67. A browser calculator, Python command-line tool, CSV processor, and FastAPI endpoint are provided.

**Research/educational utility; not a diagnostic or treatment decision system.** This repository does not grade tumours automatically. Clinical interpretation, tissue selection, cell eligibility and counting method must follow the validated protocol for the specific tumour type and specimen.

## Browser calculator

Open [web/index.html](web/index.html) in a modern browser. It works locally without a Python server.

1. Enter a **non-identifying** specimen code, positive tumour-nucleus count and total tumour-nucleus count.
2. Add one or more counting fields. The interface reports each field's index and the pooled index from **summed counts**, rather than an arithmetic mean of percentages.
3. Remove fields or export the current table to CSV. Reloading clears the page's in-memory records.

Browser computation and CSV export are entirely client-side: no API calls, remote fonts, cookies, analytics or persistent storage are used by the calculator. The separate expandable **backend audit interface** makes an HTTP request only when explicitly submitted against a local FastAPI instance; it does not run on GitHub Pages.

The browser implementation uses ordinary JavaScript, not Python or Pyodide, to avoid a heavy runtime for simple count arithmetic.

## Algorithm

`Ki-67 index (%) = (Ki-67-positive eligible tumour nuclei / total eligible tumour nuclei) × 100`

For example, **125 positive nuclei out of 500 total = 25.00%**. Inputs require non-negative whole-cell counts, a positive denominator, and positive cells no greater than total cells. The reported percentage is rounded to two decimals; retain original counts for reproducibility.

This simple count ratio **does not implement the International Ki67 Working Group's calibrated weighted-global breast-cancer scoring method** or site-specific NET grade assignment. Validity depends on representative tissue selection, counting protocol, quality control, and disease-specific interpretation. The previously implemented `v1 + v2/2 + v3/3...` calculation is kept as an **explicitly labeled legacy proxy**, **not a Ki-67 index or clinically validated grade**. Do not use legacy classifications for care decisions.

Reference: Nielsen TO, et al. *Assessment of Ki67 in Breast Cancer: Updated Recommendations From the International Ki67 in Breast Cancer Working Group*. JNCI. 2021;113:808–819. [doi:10.1093/jnci/djaa201](https://doi.org/10.1093/jnci/djaa201).

## Python

Requires Python 3.10 or newer. From a checkout:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

Single count-based evaluation:

```bash
python -m ki67_indexer single --positive-cells 125 --total-cells 500
```

Batch count-based CSV:

```bash
python -m ki67_indexer batch -i sample.csv -o results.csv
```

The input CSV must have both `positive_cells` and `total_cells` headers. Non-measurement columns (such as `sample_id`) are retained in output but excluded from calculations. Invalid counts fail validation. For compatibility, a CSV with `v1`, `v2`, etc. is processed in legacy-proxy mode, clearly marked by the output `method` column. CSVs with incomplete count headers are rejected.

From Python:

```python
from ki67_indexer import calculate_index, calculate_metrics

count_result = calculate_index(125, 500)
assert count_result["score"] == 25.0
assert count_result["method"] == "positive_over_total"

# Backward compatibility only — not a Ki-67 labeling index:
legacy = calculate_metrics(v1=10, v2=6)
assert legacy["method"] == "legacy_weighted_proxy_not_ki67"
```

## Optional FastAPI service

Set a cryptographically random audit key before using the **separate legacy generic audit service**:

```bash
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
python cli.py serve --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/` for the same browser interface. FastAPI also provides:

| Endpoint | Function |
| --- | --- |
| `POST /api/ki67` | Validated count-based index from `{"positive_cells":125,"total_cells":500}` |
| `GET /health` | Server health |
| `GET /metrics` | In-process demonstration counters |
| `POST /api/audit` | Legacy generic multi-worker audit (not Ki-67 grading) |
| `POST /api/chat` | Deterministic **mock** response; no LLM inference or verification |
| `GET /api/audit/logs` | In-memory HMAC-chain metadata and integrity result |
| `GET /docs` | Automatically generated API documentation |

The generic audit is available through `python cli.py audit`, `python cli.py batch` (audit-task CSV, **not** cell-count CSV), and `python cli.py verify-audit`. The `ki67-indexer` installed console command points to this legacy CLI for backward compatibility.

`AUDIT_SECRET_KEY` is required for audit signing; plain counting can run without it. The audit log is **in-memory and is lost on restart**, not a durable clinical record. HMAC verification detects modifications to signed metadata in memory, but it is not independent evidence of record retention or completeness. The PHI-pattern guard is heuristic and **does not establish HIPAA de-identification or protect every form of PHI**. Do not enter or upload identifiable patient data.

Docker Compose exposes the optional API on localhost only:

```bash
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
docker compose up --build
```

Do not expose the demo audit service to untrusted networks without additional access controls and operational security review.

## Tests and development

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m compileall -q .
```

The GitHub Actions test workflow covers Python 3.10–3.12, including count arithmetic, invalid inputs, CSV handling, API responses and tamper detection. A separate workflow publishes the contents of `web/` to GitHub Pages when Pages is enabled for GitHub Actions deployment.

The browser calculator needs no build step and is intended for current versions of Chrome, Edge, Firefox and Safari; a cross-browser test matrix is not currently automated.

## Project layout

- `ki67_indexer.py` — count-based arithmetic and backward-compatible legacy CLI
- `web/index.html` — static browser calculator
- `agents/api.py` — FastAPI service, count endpoint and legacy audit API
- `agents/`, `enrichment.py`, `cli.py` — legacy mock/audit demonstration modules
- `tests/`, `test_ki67_indexer.py` — automated regression tests
- `sample.csv` — synthetic, non-identifying count data
- `.github/workflows/` — tests and Pages publishing

## License

[MIT](LICENSE).
