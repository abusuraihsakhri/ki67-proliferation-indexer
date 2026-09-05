# Ki67 Proliferation Indexer

> **Domain:** Medical Oncology & Cancer Staging Systems
> **Reference Guidelines:** AJCC Cancer Staging Manual & NCCN Clinical Practice Guidelines

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## What It Does

Ki-67 Proliferation Indexer calculates Ki-67 labeling index (%) from cell counts with breast/NET grading cutoffs. It provides:

- **Single case evaluation** - Calculate Ki-67 score from individual measurements
- **Batch processing** - Process multiple patient records from CSV files
- **Clinical classification** - Automatic grading (Low/Moderate/High) based on standard cutoffs
- **REST API** - FastAPI-based HTTP service for integration
- **Audit trail** - Tamper-evident HMAC-SHA256 logging of all operations
- **PHI protection** - Zero-PHI outbound guard preventing accidental data leakage

Author: Dr. Abu Suraih Sakhri | License: MIT

---

## Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/ki67-proliferation-indexer.git
cd ki67-proliferation-indexer

# Install dependencies
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### Environment Setup

Create a `.env` file (see `.env.example`):

```bash
# Required: Secret key for HMAC-SHA256 audit signing
# Generate a secure key:
python -c "import secrets; print(secrets.token_hex(32))"
export AUDIT_SECRET_KEY="your-generated-key-here"

# Optional: Model provider (mock, ollama, claude, openai)
export MODEL_PROVIDER=mock
```

---

## Usage

### Command Line Interface

#### Single Case Evaluation
```bash
# Using defaults
python -m ki67_indexer single

# With custom values
python -m ki67_indexer single --v1 14.5 --v2 4.2 --v3 1.8
```

#### Batch Processing
```bash
python -m ki67_indexer batch -i sample.csv -o results.csv
```

#### Enterprise CLI (with audit trail)
```bash
# Run audit evaluation
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2

# Batch processing with audit
python cli.py batch -i sample.csv -o results.csv

# Verify audit trail integrity
python cli.py verify-audit

# Start API server
python cli.py serve --host 127.0.0.1 --port 8000
```

### REST API

```bash
# Start the server
python cli.py serve
```

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/metrics` | GET | Prometheus-style metrics |
| `/api/audit` | POST | Submit task for evaluation |
| `/api/chat` | POST | Query the supervisor |
| `/api/audit/logs` | GET | View audit trail |

### Python API

```python
from ki67_indexer import calculate_metrics

# Calculate Ki-67 score
result = calculate_metrics(v1=14.5, v2=4.2, v3=1.8)
print(result["score"])           # 17.07
print(result["classification"])  # "Moderate / Intermediate"
```

---

## Algorithm

The Ki-67 score is computed as a weighted sum of input values:

```
score = v1 + (v2 / 2) + (v3 / 3) + ...
```

**Classification Cutoffs:**
| Range | Classification | Recommendation |
|-------|---------------|----------------|
| < 10% | Low / Standard | Standard monitoring |
| 10-25% | Moderate / Intermediate | Close observation |
| > 25% | High / Severe | Urgent clinical intervention |

---

## Input Data Schema

### CSV Batch Format

| Field | Description | Requirement |
|:------|:------------|:------------|
| `Patient_ID` | Patient identifier | Required |
| `v1` | Primary Ki-67 value (0-100%) | Required |
| `v2` | Secondary Ki-67 value (0-100%) | Optional |
| `v3` | Tertiary Ki-67 value (0-100%) | Optional |

See `sample.csv` for an example.

---

## Security Features

- **Zero-PHI Outbound Guard:** AST and regex inspection blocking SSNs, MRNs, phone numbers, emails, and patient identifiers
- **HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation
- **Input Validation:** All Ki-67 values validated to be within [0, 100] range
- **Secure Defaults:** No hardcoded secrets; audit key must be provided via environment

---

## Testing

```bash
# Run all tests
pytest -v

# Run with coverage
pytest -v --cov=.

# Run specific test files
pytest test_ki67_indexer.py -v
pytest tests/ -v
```

### Simulation Benchmark

```bash
# Run high-throughput simulation (100 tasks)
python simulator.py 100
```

---

## Docker Deployment

```bash
# Build and run with Docker Compose
export AUDIT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
docker-compose up --build

# Or with Docker directly
docker build -t ki67-proliferation-indexer .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY=$AUDIT_SECRET_KEY ki67-proliferation-indexer
```

---

## Project Structure

```
ki67-proliferation-indexer/
├── ki67_indexer.py      # Core algorithm and CLI
├── cli.py               # Enterprise CLI with audit
├── enrichment.py        # Enrichment engines
├── simulator.py         # Load testing simulator
├── agents/              # Multi-agent architecture
│   ├── base.py          # Security, PHI guard, audit
│   ├── models.py        # Pydantic schemas
│   ├── supervisor.py    # Orchestrator
│   ├── workers.py       # Domain workers
│   ├── api.py           # FastAPI endpoints
│   └── ...
├── tests/               # Test suite
├── web/                 # Operations console UI
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```
