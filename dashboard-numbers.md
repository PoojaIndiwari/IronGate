# Dashboard numbers — IronGate Person B

Fill this table in at the end of Day 2. The numbers matter more than
the tool: if Grafana + Loki install quickly, use them; if not, this
table in your README is the dashboard. Every number below must come
from a real run, not a guess.

| # | Number | Value | Where it comes from |
|---|---|---|---|
| 1 | Images signed (%) | 100% - 1 signed image deployed, 1 unsigned denied | Signed image ghcr.io/poojaindiwari/irongate@sha256:19c63ca7bc3b224f95b925c1970cfb15c409fd45889e83f51fa20bbc113b5156 verified 2026-11-27 with examples/verify.sh (exit 0): cosign verify signature, verify-attestation slsaprovenance1, verify-attestation spdxjson, signer https://github.com/PoojaIndiwari/IronGate/.github/workflows/release.yml@refs/heads/main, issuer https://token.actions.githubusercontent.com. Deployed by digest in paynest-demo, pods Running 1/1, /health {"status":"ok"}. Evidence: evidence/cosign-verify.txt. |
| 2 | Blocked deployments | 3 proven live | 1 Kyverno block-latest-tag denial (test-latest.yaml, nginx:latest, 2026-11-26) + 1 Pod Security restricted denial (privileged escape pod, Attack 3, 2026-11-27) + 1 ValidatingAdmissionPolicy denial (unsigned image ghcr.io/poojaindiwari/irongate:latest, proof-check-unsigned, 2026-11-27: "PayNest requires the approved repository and an immutable SHA-256 digest."). block-privileged ValidatingPolicy is READY true but its denial was not separately proven live - the privileged pod was stopped by Pod Security first. |
| 3 | Mean time to detect (MTTD) | Under 1 second | Shell 06:26:17 to 06:26:17.958, miner 06:28:11 to 06:28:12.134, token 06:37:04 to 06:37:04.501, IMDS 06:37:10 to 06:37:10.355, escape rule 06:39:02 to 06:39:02.656. All under 1s, 1-second start-time resolution. IMDS in paynest also under 1s: 06:57:43 to 06:57:44.229, and 07:01:24 to 07:01:24.390. |
| 4 | Mean time to contain (MTTC) | About 38 seconds, manual | IMDS alert 07:01:24.390 to pod deleted 07:02:02 (manual steps: label, isolate, save evidence, delete). Includes the 5-second curl timeout. This is one manual run, not an average. |
| 5 | Detection coverage | 4/5 alerted, 5/5 stopped | Shell, miner, token, IMDS alerted. Attack 3 (privileged escape pod) did not alert - it was blocked at admission by Pod Security restricted, so it never ran. Rule 6 escape attempt also fired separately at 06:39:02 (cat /proc/1/root and nsenter). Note: shell rule also fired 4 times at 06:35:51 for sh -c stty -a, parent=frontend, which the user did not run - unexplained, needs tuning. Miner port half only fires on a completed connection; IMDS in paynest only fires with curl, not wget/nc in the nginx image. |

## STRIDE note — runtime half (shared work, Section 6)

PayNest at runtime is most exposed in two STRIDE areas. **Spoofing:**
an unsigned or tampered image can pretend to be PayNest — that is
why admission only lets signed images run, and why a pod that
cannot prove its signature is rejected before it starts, not after.
**Elevation of Privilege:** a pod that gets a shell, reads the
service-account token, or tries to break out of its container
(`nsenter`, `/proc/1/root`) can gain more rights than the app was
given — that is why Pod Security is `restricted`, Kyverno blocks
privileged containers and host paths, and Falco watches for shell
access, token reads, and escape attempts, with the auto-response
script isolating and killing the pod when one fires.