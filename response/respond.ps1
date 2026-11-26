# Day 2 afternoon — auto-response for a bad pod.
# Run from the irongate-person-b-starter-files folder in VS Code PowerShell:
#   .\response\respond.ps1 -PodName <pod-name> -Namespace paynest
# What it does, in the guide's order:
#   1. Label the pod quarantine=true (isolate.yaml then blocks all its traffic)
#   2. Save pod logs + pod description to evidence\  (this replaces S3 on a laptop)
#   3. Kill the pod
#   4. Credential rotation is NOT automatic here — after it runs, rotate the
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

Write-Host "2. Applying isolate NetworkPolicy ..."
kubectl apply -f (Join-Path $Root "networkpolicies\isolate.yaml")

Write-Host "3. Saving evidence to evidence\ ..."
kubectl logs $PodName -n $Namespace > (Join-Path $EvidenceDir "$PodName-logs.txt")
kubectl describe pod $PodName -n $Namespace > (Join-Path $EvidenceDir "$PodName-describe.txt")
kubectl get pod $PodName -n $Namespace -o yaml > (Join-Path $EvidenceDir "$PodName.yaml")

Write-Host "4. Killing pod $PodName ..."
kubectl delete pod $PodName -n $Namespace

Write-Host "Done. Evidence saved in evidence\. Now rotate the exposed test secret by hand."
