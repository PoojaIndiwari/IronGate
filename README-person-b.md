# IronGate — Person B starter files (2-day, laptop only)

Copy this whole folder into VS Code as `irongate-person-b`.
It matches the 2-day guide exactly: same file names, same order.
Work in this order: cluster first, then admission, then Falco, then response.

## Replace these 3 things first

1. `YOUR-REGISTRY` — in `policies/verify-signature.yaml`,
   `policies/allowed-registry.yaml` and `app/paynest-test.yaml`.
   Use the registry from `SIGNING-CONTRACT.md`.
2. `PASTE-THE-WHOLE-CONTENTS-OF-cosign.pub-HERE` — in
   `policies/verify-signature.yaml`. Public key only. Never put
   `cosign.key` (the private key) in this repo.
3. The image tag in `app/paynest-test.yaml` — use the tag you signed,
   for example `:test1`. Never `:latest`.

Signing needs a registry: Cosign signs an image that is pushed to a
registry. For the laptop test, push your test image to a registry you
can reach from kind (for example a local registry, or the registry
Person A uses), then sign that exact image name + tag.

## Apply in this order

Day 1 morning — create the cluster FIRST, then apply the files:
```
kind create cluster --name irongate
kubectl apply -f cluster/namespaces.yaml
kubectl apply -f networkpolicies/default-deny.yaml
kubectl apply -f networkpolicies/allow-paynest.yaml
```
Test first: a normal pod runs in paynest, a privileged pod is blocked.

Day 1 afternoon (Kyverno must be installed first — see the guide):
```
kubectl apply -f policies/verify-signature.yaml
kubectl apply -f policies/block-latest.yaml
kubectl apply -f policies/block-privileged.yaml
kubectl apply -f policies/allowed-registry.yaml
kubectl apply -f app/paynest-test.yaml
```
Test: unsigned = blocked, signed = runs, `:latest` = blocked.
Save the unsigned-rejection log in `evidence\` — that is Scenario 2.

Day 1 evening (Falco must be installed first — see the guide):
Load `falco/custom-rules.yaml` through Helm customRules (see the
comment at the top of that file), then test: open a shell in a pod,
a Falco alert must appear within seconds.

Day 2 morning — attacks, only in your own kind cluster:
```
kubectl create namespace attack-test
```
Run the 5 attacks from the guide, one by one. For each one save:
command you ran, Falco alert, time you started, time the alert fired.
Delete the namespace when you finish:
`kubectl delete namespace attack-test`

Day 2 afternoon — auto-response, test it with Attack 5 (IMDS):
```
.\response\respond.ps1 -PodName <pod-name> -Namespace paynest
```
It labels the pod quarantine=true, applies the isolate policy,
saves logs to `evidence\`, then kills the pod. Rotate the test
secret by hand after it runs.

## Tables for your README / demo

MITRE mapping (from falco/custom-rules.yaml):
| Rule | MITRE |
|---|---|
| Shell in a container | T1059 Execution |
| Contact IMDS 169.254.169.254 | T1552 Credential Access |
| Write to system folders | T1543 Persistence |
| Crypto miner signs | T1496 Impact |
| Read service-account token | T1552 Credential Access |

Coverage table — fill in one row per attack:
| Attack | Rule | Alert fired? | Time to detect |
|---|---|---|---|
| 1 Reverse shell | Shell in container | | |
| 2 Crypto miner | Crypto miner signs | | |
| 3 Container escape | Blocked by admission / Falco | | |
| 4 RBAC abuse | Token / secret access | | |
| 5 IMDS theft | Contact IMDS | | |

5 numbers for the dashboard:
| Number | Value |
|---|---|
| Images signed (%) | |
| Blocked deployments | |
| Mean time to detect | |
| Mean time to contain | |
| Detection coverage (alerts / 5) | |

## If something breaks

- Kyverno blocks your good image too: the image name/tag must match
  the contract exactly, and the signature must be for that exact tag.
- Kyverno rejects verify-signature.yaml: your Kyverno version may
  need the newer `imageReferences` / `attestors` form instead of
  `image:` / `key:`. Tell Muse your Kyverno version.
- Falco pods crash-loop: try `driver.kind=ebpf` (see the guide).
  Time-box driver problems to 30 minutes.
- Prowler is skipped on purpose: laptop-only build, no AWS account.
  Write that one line in your README.
