"""Classify sanitized Kubernetes audit records. Reads input as data."""
import json
import sys
from pathlib import Path

READ_VERBS = {"get", "list", "watch"}


def classify(event):
    target = event.get("objectRef", {})
    if (
        event.get("stage") != "ResponseComplete"
        or event.get("verb") not in READ_VERBS
        or target.get("namespace") != "paynest-demo"
        or target.get("resource") != "secrets"
    ):
        return None
    code = event.get("responseStatus", {}).get("code")
    if code == 403:
        return "denied-secret-read"
    if code == 200:
        # Successful reads are informational: review who read which Secret.
        return "allowed-secret-read"
    return None


def replay(path):
    failures = 0
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if not rows:
        raise ValueError("Fixture file is empty")
    for row in rows:
        actual = classify(row["event"])
        passed = actual == row["expected"]
        print(f"{'PASS' if passed else 'FAIL'} {row['case']} -> {actual or 'quiet'}")
        failures += int(not passed)
    return failures


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("audit-cases.jsonl")
    sys.exit(1 if replay(path) else 0)
