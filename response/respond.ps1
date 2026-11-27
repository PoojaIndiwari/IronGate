# Day 2 afternoon — auto-response for a bad pod.
# Run from the irongate-person-b-starter-files folder in VS Code PowerShell:
#   .\response\respond.ps1 -PodName <pod-name> -Namespace paynest
# WARNING: pod YAML dumps can contain secrets (env vars, tokens, mounted
# secrets). Evidence saved by this script goes in evidence\, which is in
# .gitignore. Never commit evidence\.
# What it does, in the guide's order:
#   1. Label the pod quarantine=true (isolate.yaml then blocks all its traffic)
#   2. Remove the app label, so the pod stops matching the allow rules.
#      WHY: NetworkPolicies only ADD allowed traffic. A pod labelled
#      quarantine=true still matches app=paynest-backend, so the
#      allow-frontend-to-backend / allow-backend-to-db rules keep working
#      and isolate.yaml blocks nothing. Removing the app label is what
#      actually cuts it off from the allow rules.
#      It also tries to remove an irongate.io/network label, if one is
#      present; that step is ignored if the label does not exist.
#   3. Apply the isolate NetworkPolicy
#   4. Save pod logs + pod description to evidence\ (this replaces S3 on a laptop)
#      — saved with Out-File -Encoding utf8, NOT with `>` redirects.
#      Windows PowerShell 5.1 writes `>` redirects as UTF-16, which makes
#      the logs unreadable in most editors.
#   5. Kill the pod
#   6. Credential rotation is NOT automatic here — after it runs, rotate the
#      test secret by hand and write that step in your README. Say so in the demo.
param(
  [Parameter(Mandatory = $true)][string]$PodName,
  [string]$Namespace = "paynest"
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$EvidenceDir = Join-Path $Root "evidence"
New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null

Write-Host "1. Labelling pod $PodName quarantine=true ..."
kubectl label pod $PodName -n $Namespace quarantine=true --overwrite

Write-Host "2. Removing the app label so allow NetworkPolicies stop matching this pod ..."
kubectl label pod $PodName -n $Namespace app- --overwrite
# Also remove the irongate.io/network label if it is present.
# If it is not present kubectl returns an error for this one label only;
# that is expected — ignore it and continue.
kubectl label pod $PodName -n $Namespace irongate.io/network- --overwrite 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Host "   (irongate.io/network label was not present — continuing.)"
}

Write-Host "3. Applying isolate NetworkPolicy ..."
kubectl apply -f (Join-Path $Root "networkpolicies\isolate.yaml")

Write-Host "4. Saving evidence to evidence\ (UTF-8) ..."
kubectl logs $PodName -n $Namespace | Out-File -Encoding utf8 -FilePath (Join-Path $EvidenceDir "$PodName-logs.txt")
kubectl describe pod $PodName -n $Namespace | Out-File -Encoding utf8 -FilePath (Join-Path $EvidenceDir "$PodName-describe.txt")
kubectl get pod $PodName -n $Namespace -o yaml | Out-File -Encoding utf8 -FilePath (Join-Path $EvidenceDir "$PodName.yaml")

Write-Host "5. Killing pod $PodName ..."
kubectl delete pod $PodName -n $Namespace

Write-Host "Done. Evidence saved in evidence\. Now rotate the exposed test secret by hand."
Write-Host "Do NOT commit evidence\ — it can contain secrets. See .gitignore."
