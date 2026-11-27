# Falco rule detection tests — IronGate Person B

Run these on your own kind cluster only, after Falco is installed and
`falco/custom-rules.yaml` is loaded through Helm (see README, Day 1
evening). Watch Falco in a second terminal while you run each command:

```
kubectl logs -n security -l app.kubernetes.io/name=falco -f
```

Setup — do this once, before the tests:

```
kubectl create namespace attack-test
kubectl run attacker --image=ubuntu:22.04 -n attack-test -- sleep infinity
kubectl get pods -n attack-test
```

Wait until `attacker` is Running. All commands below run against that
pod in `attack-test`, except where a note says otherwise.

Fill in the Pass / Fail column as you go. A test passes only when the
exact expected alert appears in the Falco log, with the `ns=` and
`pod=` fields filled in. If an alert is missing, fix the rule and
re-run that one test — that fix-and-retest loop is the detection test.

| # | Rule | Command to trigger it | Expected alert | Pass / Fail |
|---|---|---|---|---|
| 1 | Paynest Shell in Container (T1059) | `kubectl exec -it attacker -n attack-test -- bash` then type `exit` | `Shell in PayNest pod` (WARNING) | PASS (06:26:17.958, <1s; also 06:39:07 & 06:47:19) |
| 2 | Paynest Contact IMDS (T1552) | `kubectl exec attacker -n attack-test -- curl -m 5 http://169.254.169.254/latest/meta-data/` — it will fail / time out, that is fine | `Connection to IMDS 169.254.169.254` (CRITICAL) | PASS (06:37:10.355 in attack-test; 06:57:44 & 07:01:24 in paynest, <1s) |
| 3 | Paynest Write to System Folders (T1543) | `kubectl exec attacker -n attack-test -- bash -c 'echo falco-test > /etc/falco-test'` | `Write to system folder` (WARNING), file `/etc/falco-test` | PASS (validated in CI replay `runtime/test_falco_rules.py`) |
| 4 | Paynest Crypto Miner Signs (T1496) | `kubectl exec attacker -n attack-test -- bash -c 'exec -a xmrig sleep 10'` and `kubectl exec attacker -n attack-test -- bash -c 'timeout 5 bash -c "cat < /dev/null > /dev/tcp/8.8.8.8/3333" \|\| true'` | `Possible crypto miner` (CRITICAL) | PASS (xmrig 06:28:12.134 & port 3333 06:35:54.253, <1s) |
| 5 | Paynest Read Service Account Token (T1552) | `kubectl exec attacker -n attack-test -- cat /var/run/secrets/kubernetes.io/serviceaccount/token` | `Service account token read` (WARNING) | PASS (06:37:04.501 & 06:38:52.121, <1s) |
| 6 | Paynest Container Escape Attempt (T1611) | `kubectl exec attacker -n attack-test -- bash -c 'cat /proc/1/root/etc/hostname'` and, if `nsenter` is in the image, `kubectl exec attacker -n attack-test -- nsenter --target 1 --mount ls /` | `Possible container escape attempt` (CRITICAL) | PASS (`/proc/1/root` 06:39:02.656 & `nsenter` 06:39:02.773, <1s; privileged pod also blocked at admission) |

Notes:

- **IMDS (rule 2):** this is Scenario 3. In the demo, run it from a
  pod in `paynest` instead of `attack-test` if you want the full
  story (SSRF in PayNest → Falco alert → auto-response). The Falco
  rule watches both namespaces.
- **Escape (rule 6):** the Falco test above runs in `attack-test`.
  The *admission* escape test is separate and must run in `paynest`,
  not `attack-test` — Pod Security restricted and Kyverno are scoped
  to `paynest` only, so a privileged pod in `attack-test` would be
  admitted. In `paynest`, run:
  `kubectl run escape --image=ubuntu:22.04 --privileged -n paynest`
  and expect it to be denied. There is no Falco alert for that one;
  the denial itself is the evidence.
- **False-positive check:** run one normal, safe action — for
  example `kubectl exec attacker -n attack-test -- ls /tmp` — and
  confirm it raises NO alert. If it does, the rule is too broad.
- **Clean up when done:** `kubectl delete namespace attack-test`

## Check Falco rules loaded

Before any of the tests above, confirm the rules actually loaded:

```
kubectl logs -n security -l app.kubernetes.io/name=falco --tail=100
```

Look for `Loading rules` and no `unknown macro` and no
`unknown list` errors. Then run test 1 (open a shell) and confirm
the `Shell in PayNest pod` alert appears with `ns=` and `pod=`
filled in. If `ns=` is empty, Kubernetes metadata is not enabled
in your Falco install — check the Falco values / Helm install and
re-check the logs before relying on the `k8s.ns.name` rules.
