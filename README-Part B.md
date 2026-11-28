# IronGate — Part B

Copy this whole folder into VS Code as `irongate-person-b`.
It matches the 2-day guide exactly: same file names, same order.
Work in this order: cluster first, then admission, then Falco, then response.

## Open question — namespace name

This starter uses namespace `paynest`. Person A's repo uses
`paynest-demo` in some places. Do NOT rename the namespace in this
starter — that is an open question for the user and Person A to agree
on. If you agree on `paynest-demo`, rename it everywhere (namespaces,
policies, NetworkPolicies, Falco rule list, test files) in one go,
or the policies and rules will stop matching the pods.

## Kyverno v1.20 — read this first

These policies use the Kyverno v1.20 CEL format, not the old
legacy ClusterPolicy format. In Kyverno v1.20 the old format is
not enforced at all — it can be read, listed and deleted, but
it will not block anything, and you cannot create or update it.
That is why the block-latest test failed at first, and why it
passed once it was rewritten in the new format.

New policy kinds:
- `policies/block-latest.yaml` — Kyverno `ValidatingPolicy` (Deny, scoped to `paynest` and `paynest-demo`)
- `policies/block-privileged.yaml` — Kyverno `ValidatingPolicy` (Deny, scoped to `paynest` and `paynest-demo`)
- `runtime/proof-policy.yaml.in` — Kubernetes `ValidatingAdmissionPolicy` (`irongate-source`) + Kyverno keyless `ImageValidatingPolicy` (`irongate-proof` verifying Cosign signature, SLSA v1 provenance, and SPDX SBOM in `paynest-demo`)

If you already applied the old legacy policies, delete them first:
```
kubectl delete clusterpolicy block-latest-tag block-privileged
```
Then apply the files in this folder. Check the new ones with:
```
kubectl get validatingpolicies
kubectl get imagevalidatingpolicies
```

## Secrets and evidence — read this before you commit

- Never commit `cosign.key` (the private key) or any secret.
- Never commit `evidence/` — pod YAML dumps can contain secrets
  (env vars, tokens, mounted secrets).
- `.gitignore` in this folder already excludes: `evidence/`,
  `cosign.key`, `*.key`, `*.pem`, `.env`. Check `git status`
  before every commit and confirm none of those show up.
- On Windows PowerShell 5.1, `>` redirects write UTF-16, which
  makes logs unreadable. Save logs with
  `Out-File -Encoding utf8` instead — `response/respond.ps1`
  already does this for the evidence it saves.

## Signing: keyless, by digest (no keys to replace)

Signing is keyless and happens in `.github/workflows/release.yml`. There is no `cosign.key`,
no `cosign.pub`, and no `YOUR-REGISTRY` placeholder to fill in. The cluster trusts one
identity, written down in `SIGNING-CONTRACT.md`:

- image by immutable digest: `ghcr.io/<owner>/irongate@sha256:<64 hex>`
- signer: the GitHub workflow identity of `release.yml` on `refs/heads/main`
- required: signature + SLSA v1 provenance + SPDX SBOM

`examples/render_demo.py OWNER/REPO IMAGE@sha256:...` renders `runtime/proof-policy.yaml.in`
and the manifests into `local-output/` (git-ignored). Apply `local-output/admission.yaml`
to enforce the contract in `paynest-demo`.

## Apply in this order

Day 1 morning — create the cluster FIRST, then apply the files:
```
kind create cluster --name irongate
kubectl apply -f cluster/namespaces.yaml
kubectl apply -f networkpolicies/default-deny.yaml
kubectl apply -f networkpolicies/allow-paynest.yaml
kubectl apply -f networkpolicies/allow-frontend-egress.yaml
```
`allow-frontend-egress.yaml` is needed: `default-deny` blocks ALL
egress, and `allow-paynest.yaml` only gives the backend an egress
rule (to the db, plus DNS). Without this file the frontend cannot
reach the backend on 8080 at all. This file allows the frontend
egress to the backend on TCP 8080, plus DNS to kube-system on 53.

NetworkPolicy note: kind's default CNI does enforce NetworkPolicies.
If a pod can still talk after `default-deny` is applied, check
`kubectl get pods -n kube-system` — look for what CNI is running
(Calico / Cilium / kindnet) and confirm it is actually up.

Test first: a normal pod runs in paynest, a privileged pod is blocked.

Day 1 afternoon (Kyverno must be installed first, see the guide):
```
kubectl apply -f policies/block-latest.yaml
kubectl apply -f policies/block-privileged.yaml
```
Test: `:latest` = blocked by `block-latest-tag` (the message must say so, not just
"violates PodSecurity").

The signature gate is separate. Render it from the contract and apply it:
```
python3 examples/render_demo.py OWNER/REPO ghcr.io/owner/irongate@sha256:<digest>
kubectl apply -f local-output/namespace.yaml
kubectl apply -f local-output/admission.yaml
```
Test: signed digest = admitted, tag-only = denied by `irongate-source`, unsigned digest =
denied by `irongate-proof`. The `signature-gate` job in
`.github/workflows/person-b-runtime.yml` runs all three on every change. Save the
unsigned-rejection log in `evidence\` (that is Scenario 2) and do not commit `evidence\`.

Day 1 evening (Falco must be installed first — see the guide):
Load `falco/custom-rules.yaml` through Helm customRules (see the
comment at the top of that file), then test: open a shell in a pod,
a Falco alert must appear within seconds.

### Check Falco rules loaded

Before you trust any alert, confirm the rules loaded:

```
kubectl logs -n security -l app.kubernetes.io/name=falco --tail=100
```

Look for `Loading rules` and no `unknown macro` and no
`unknown list` errors. The custom rules use `k8s.ns.name` and the
`shell_binaries` list, which depend on your Falco version and on
Kubernetes metadata being enabled — confirm both appear in an
alert before relying on them.

Canary test: open a shell in a test pod (see `falco/test-rules.md`,
test 1) and confirm the `Shell in PayNest pod` alert appears with
`ns=` and `pod=` filled in. If `ns=` is empty, Kubernetes metadata
is not enabled in your Falco install — check the Falco values /
Helm install and re-check the logs.

Day 2 morning — attacks, only in your own kind cluster:
```
kubectl create namespace attack-test
```
Run the 5 attacks from the guide, one by one. For each one save:
command you ran, Falco alert, time you started, time the alert fired.
Delete the namespace when you finish:
`kubectl delete namespace attack-test`

**Attack 3 correction — run it in `paynest`, not `attack-test`.**
Pod Security restricted and Kyverno are scoped to `paynest` only.
A privileged pod in `attack-test` is admitted, so it proves nothing.
Run Attack 3 in `paynest`:
```
kubectl run escape --image=ubuntu:22.04 --privileged -n paynest
```
Expect it to be denied. The Falco escape test (nsenter /
`/proc/1/root`, rule 6 in `falco/test-rules.md`) is separate and
does run in `attack-test`.

Full detection tests for all 6 Falco rules are in
`falco/test-rules.md` — use that table, not just the guide.

Day 2 afternoon — auto-response, test it with Attack 5 (IMDS):
```
.\response\respond.ps1 -PodName <pod-name> -Namespace paynest
```
It labels the pod quarantine=true, **removes the `app` label**,
applies the isolate policy, saves logs to `evidence\` (UTF-8),
then kills the pod. Rotate the test secret by hand after it runs.

Why the `app` label is removed: NetworkPolicies only add allowed
traffic. A pod labelled quarantine=true still matches
`app=paynest-backend`, so the allow rules keep working and
`isolate.yaml` blocks nothing. Removing the `app` label is what
actually cuts it off.

Traffic-stop test: before quarantine, curl frontend -> backend on
8080 and confirm it works. After `respond.ps1` runs, curl again
from the same pod (before it is killed, or re-create the same pod
and quarantine it without killing) — it must fail / time out.
If traffic still flows, the label was not removed.

## CI for this half

`.github/workflows/person-b-runtime.yml` runs on push / pull request (and on demand):

1. `detection-as-code`: replays the Kubernetes audit fixtures and replays the Falco fixtures
   through the real rule conditions in `falco/custom-rules.yaml` (`runtime/falco_eval.py`).
   Changing a rule changes what is tested.
2. `runtime-checks` (kind + Kyverno): `:latest` is denied by `block-latest-tag`; a privileged
   pod and a `hostPID` pod are denied by `block-privileged` with Pod Security relaxed for that
   step, so Kyverno is the only gate left; Pod Security `restricted` is then shown to block the
   same pod on its own; a compliant pod runs. Every denial must carry the expected message.
3. `signature-gate` (kind + Kyverno, needs internet): the signed release digest from
   `SIGNING-CONTRACT.md` is admitted (server-side dry run), a tag-only image is denied, and an
   unsigned digest is denied by signature verification.

kind, kubectl and Helm are downloaded at pinned versions and checked against the checksum
files their projects publish (`runtime/ci-helpers.sh`). Kyverno is installed from the newest
chart on the 1.20 line and the chart version is written to the run summary.

Limits: the Falco replay proves the *rule logic* against recorded events. It cannot prove that a
real Falco build supplies a field. That is what `falco/test-rules.md` on a live cluster is for.

## Tables for your README / demo

MITRE mapping (from falco/custom-rules.yaml — 6 rules now):
| Rule | MITRE |
|---|---|
| Shell in a container | T1059 Execution |
| Contact IMDS 169.254.169.254 | T1552 Credential Access |
| Write to system folders | T1543 Persistence |
| Crypto miner signs | T1496 Impact |
| Read service-account token | T1552 Credential Access |
| Container escape attempt | T1611 Privilege Escalation |

Coverage table — filled from live run (`evidence/falco-attacks.txt`, `evidence/attack3-escape-denied.txt`):
| Attack | Rule | Alert fired? | Time to detect |
|---|---|---|---|
| 1 Reverse shell | Shell in container (T1059) | Yes | < 1s (06:26:17.958) |
| 2 Crypto miner | Crypto miner signs (T1496) | Yes (`xmrig` + port 3333; stratum command line added, re-run pending) | < 1s (06:28:12.134) |
| 3 Container escape | Blocked by admission (in `paynest`) + Container Escape Attempt (Falco T1611) | Blocked at admission; Falco escape rule also fired separately | < 1s (06:39:02.656) |
| 4 RBAC / token abuse | Service account token read (T1552) + audit replay (`runtime/audit.py`) | Yes | < 1s (06:37:04.501) |
| 5 IMDS theft | Contact IMDS (T1552) | Yes with curl (`attack-test` + `paynest`); wget/nc/bash covered by the exec half, live re-run pending | < 1s (06:37:10.355 / 07:01:24.390) |

5 numbers for the dashboard — see `dashboard-numbers.md` and `monitoring/grafana-dashboard.json`:
| Number | Value |
|---|---|
| Images signed (%) | 100% (1 signed digest deployed, 1 unsigned denied) |
| Blocked deployments | 3 proven live (`block-latest`, Pod Security `restricted`, `irongate-source`) |
| Mean time to detect | Under 1 second |
| Mean time to contain | About 38 seconds (manual `respond.ps1`; automated Falco Talon rules in `response/falco-talon-rules.yaml`) |
| Detection coverage (alerts / 5) | 4/5 alerted, 5/5 stopped (Attack 3 blocked before start) |

## If something breaks

- Kyverno blocks your good image too: the image must be the exact digest from
  the contract and the policy must be rendered with the same OWNER/REPO.
- Kyverno says a policy is deprecated / not enforced: you are
  looking at an old legacy-format file. Only the CEL files in
  `policies/` and the policy rendered from `runtime/proof-policy.yaml.in` work on Kyverno v1.20. Delete any
  old legacy policy and apply the matching file from this folder.
- Falco pods crash-loop: try `driver.kind=ebpf` (see the guide).
  Time-box driver problems to 30 minutes.
- Falco alert has empty `ns=`: see "Check Falco rules loaded" above.
- Frontend cannot reach backend: check
  `networkpolicies/allow-frontend-egress.yaml` is applied, and
  that the frontend pod really has label `app=paynest-frontend`.
- Quarantined pod can still talk: check the `app` label was
  removed (`kubectl get pod <name> -n paynest --show-labels`).
- Prowler is skipped on purpose: laptop-only build, no AWS account.
