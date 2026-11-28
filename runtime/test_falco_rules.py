"""Detection-as-code validation and event replay for falco/custom-rules.yaml.

Events in falco-cases.jsonl are run through the real rule conditions (see falco_eval.py),
so changing a rule changes what this test checks."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from falco_eval import Evaluator  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "falco" / "custom-rules.yaml"
CASES_PATH = Path(__file__).with_name("falco-cases.jsonl")

REQUIRED_MITRE = {"T1059", "T1552", "T1543", "T1496", "T1611"}


def parse_rules_file(path: Path):
    """Parse list items and rule metadata from falco/custom-rules.yaml without external deps."""
    text = path.read_text(encoding="utf-8")
    lists = {}
    rules = []
    current = None
    in_block_field = None

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if raw_line.startswith("- list:"):
            in_block_field = None
            name = raw_line.split(":", 1)[1].strip()
            current = {"kind": "list", "name": name, "items": []}
            lists[name] = current["items"]
        elif raw_line.startswith("- rule:"):
            in_block_field = None
            name = raw_line.split(":", 1)[1].strip()
            current = {"kind": "rule", "rule": name}
            rules.append(current)
        elif current and raw_line.startswith("  ") and not raw_line.startswith("    "):
            in_block_field = None
            key, _, val = raw_line.strip().partition(":")
            val = val.strip()
            if current["kind"] == "list" and key == "items":
                items = [i.strip().strip("'\"") for i in val.strip("[]").split(",") if i.strip()]
                lists[current["name"]].extend(items)
            elif current["kind"] == "rule":
                if val in (">", "|"):
                    current[key] = ""
                    in_block_field = key
                elif key == "tags":
                    current[key] = [t.strip().strip("'\"") for t in val.strip("[]").split(",") if t.strip()]
                else:
                    current[key] = val
        elif current and in_block_field and raw_line.startswith("    "):
            sep = " " if current[in_block_field] else ""
            current[in_block_field] += sep + raw_line.strip()

    return lists, rules


def validate_rules(lists, rules):
    errors = []
    namespaces = set(lists.get("paynest_namespaces", []))
    for required_ns in ("paynest", "paynest-demo"):
        if required_ns not in namespaces:
            errors.append(f"paynest_namespaces missing '{required_ns}'")

    if not lists.get("paynest_shells"):
        errors.append("paynest_shells list is missing or empty")

    if len(rules) < 6:
        errors.append(f"Expected at least 6 Falco rules, found {len(rules)}")

    found_mitre = set()
    for r in rules:
        for field in ("rule", "desc", "condition", "output", "priority", "tags"):
            if not r.get(field):
                errors.append(f"Rule '{r.get('rule', '?')}' missing required field '{field}'")
        for tag in r.get("tags", []):
            if re.fullmatch(r"T\d{4}", tag):
                found_mitre.add(tag)

    missing_mitre = REQUIRED_MITRE - found_mitre
    if missing_mitre:
        errors.append(f"Missing MITRE ATT&CK tags: {sorted(missing_mitre)}")

    return errors


def evaluate_event(event, lists, rules):
    """Run the recorded event through the real condition text of every rule in the file."""
    ev = Evaluator(lists)
    return [r["rule"] for r in rules if ev.matches(r["condition"], event)]


def main():
    lists, rules = parse_rules_file(RULES_PATH)
    errors = validate_rules(lists, rules)
    if errors:
        for err in errors:
            print(f"FAIL schema: {err}")
        return 1

    print(f"PASS schema: {len(rules)} Falco rules validated, namespaces={lists['paynest_namespaces']}")

    rows = [json.loads(line) for line in CASES_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        print("FAIL replay: falco-cases.jsonl is empty")
        return 1

    failures = 0
    for row in rows:
        actual = evaluate_event(row["event"], lists, rules)
        expected = row["expected"]
        passed = actual == expected
        print(f"{'PASS' if passed else 'FAIL'} {row['case']} -> {actual or 'quiet'}")
        failures += int(not passed)

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
