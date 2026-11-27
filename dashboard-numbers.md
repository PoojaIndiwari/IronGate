# Dashboard numbers — IronGate Person B

Fill this table in at the end of Day 2. The numbers matter more than
the tool: if Grafana + Loki install quickly, use them; if not, this
table in your README is the dashboard. Every number below must come
from a real run, not a guess.

| # | Number | Value | Where it comes from |
|---|---|---|---|
| 1 | Images signed (%) | | Signed deploys ÷ total deploys you tested. Signed = a deploy that passed `verify-signature`; total = signed + unsigned deploys you tried (including the blocked ones). |
| 2 | Blocked deployments | | Count of Kyverno rejections. Count the `denied the request` lines in your terminal / `kubectl` output for block-latest, block-privileged and verify-signature, plus the Pod Security blocks if you count them separately — say which you counted. |
| 3 | Mean time to detect (MTTD) | | Average of the "time to detect" column in `falco/test-rules.md` (attack start time → Falco alert time, in seconds, averaged over the 5 attacks). |
| 4 | Mean time to contain (MTTC) | | Alert time → pod killed time in the auto-response test (`response/respond.ps1` run log). Time it from the Falco alert for the IMDS attack to the `kubectl delete pod` line in the script output. |
| 5 | Detection coverage | | Attacks with an alert ÷ 5 attacks tested (from `falco/test-rules.md`). Example: 4/5 = 80%. Say which attack missed, if any, and what you changed. |

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
