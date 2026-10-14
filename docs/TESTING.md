# Pharma-Khaato Testing & Verification Manual

## Running Automated Verification Suites

### 1. Security & Unit Verification Suite
Verifies PBKDF2 authentication, brute-force lockout, CNIC validation, input bounds, database backup & restore.

```bash
python3 scripts/test_security.py
```

### 2. Integration & End-to-End Flow Suite
Verifies full checkout lifecycle, FEFO batch selection, invoice generation, customer registration, and Khatoo payment recording.

```bash
python3 scripts/test_flow.py
```

### 3. Performance Benchmark Suite
Measures P50, P95, P99 transaction latencies for sub-millisecond counter operation.

```bash
python3 scripts/benchmark.py
```
