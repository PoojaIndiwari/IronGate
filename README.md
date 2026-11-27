# IronGate

IronGate secures the PayNest application from build to deployment. It scans code and dependencies, signs container images with Cosign + SLSA provenance + SPDX SBOM, and verifies them before they run on Kubernetes. At runtime, it detects suspicious activity with Falco (eBPF) and isolates affected workloads.

## Architecture Split

- **Person A (Pipeline & Artifacts):** Hardened CI/CD (`.github/workflows/pr-checks.yml`, `.github/workflows/release.yml`), Gitleaks, Semgrep, Trivy, Syft SBOM, SLSA v1 provenance, and Cosign keyless signing to GHCR (`ghcr.io/poojaindiwari/irongate`).
- **Person B (Runtime Defense):**
  - **Admission control:** Pod Security `restricted` (`cluster/namespaces.yaml`), default-deny & allowlist NetworkPolicies (`networkpolicies/`, `runtime/demo-network.yaml`), Kyverno `ValidatingPolicy` (`policies/block-latest.yaml`, `policies/block-privileged.yaml`), and keyless `ImageValidatingPolicy` (`runtime/proof-policy.yaml.in`).
  - **Runtime detection:** 6 MITRE ATT&CK-mapped Falco eBPF rules (`falco/custom-rules.yaml`) covering `paynest`, `paynest-demo`, and `attack-test`.
  - **Detection-as-code & CI:** Kubernetes audit replay (`runtime/audit.py`), Falco rule validation & event replay (`runtime/test_falco_rules.py`), PR admission checks in kind (`.github/workflows/person-b-runtime.yml`), and nightly detection/posture scans (`.github/workflows/person-b-nightly.yml`).
  - **Automated response:** Falco Talon event-driven quarantine/termination rules (`response/falco-talon-rules.yaml`) plus local containment script (`response/respond.ps1`) and quarantine policy (`networkpolicies/isolate.yaml`).
  - **Posture & metrics:** Kubescape baseline scan, Grafana security dashboard (`monitoring/grafana-dashboard.json`), and live measured metrics (`dashboard-numbers.md`).

> **Note on cloud posture (Prowler / CloudTrail):** Prowler and AWS CloudTrail are intentionally skipped in this laptop/kind build because no AWS account is provisioned.

## Live Security Metrics (`dashboard-numbers.md`)

| Metric | Value |
|---|---|
| Images signed (%) | 100% (signed digest verified with `examples/verify.sh`) |
| Blocked deployments | 3 proven live |
| Mean time to detect (MTTD) | < 1 second |
| Mean time to contain (MTTC) | ~38 seconds (manual run; automated via `response/falco-talon-rules.yaml`) |
| Detection coverage | 4/5 alerted, 5/5 stopped (Attack 3 blocked at admission) |

See [SIGNING-CONTRACT.md](SIGNING-CONTRACT.md) and [README-person-b.md](README-person-b.md) for setup and verification steps.
