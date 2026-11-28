# Day 2 afternoon - auto-response for a bad pod.
# Run from the irongate folder in VS Code PowerShell:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
#   .\response\respond.ps1 -PodName <pod-name> -Namespace paynest
# WARNING: pod YAML dumps can contain secrets. Evidence goes in evidence\,
# which is in .gitignore. Never commit evidence\.
# NOTE: this file is ASCII only. Do not add em dashes or other non-ASCII
# characters - PowerShell 5.1 misreads UTF-8 without BOM and the script
# fails to parse.
param(
  [Parameter(Mandatory = $true)][string]$PodName,
  [string]$Namespace = "paynest"
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$EvidenceDir = Join-Path $Root "evidence"
New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null
$Start = Get-Date

Write-Host "1. Labelling pod $PodName quarantine=true ..."
kubectl label pod $PodName -n $Namespace quarantine=true --overwrite

Write-Host "2. Removing the app label so allow NetworkPolicies stop matching this pod ..."
kubectl label pod $PodName -n $Namespace app- --overwrite
kubectl label pod $PodName -n $Namespace irongate.io/network- --overwrite 2>$null

Write-Host "3. Applying isolate NetworkPolicy in namespace $Namespace ..."
kubectl apply -n $Namespace -f (Join-Path $Root "networkpolicies\isolate.yaml")

Write-Host "4. Saving evidence to evidence\ (UTF-8) ..."
kubectl logs $PodName -n $Namespace | Out-File -Encoding utf8 -FilePath (Join-Path $EvidenceDir "$PodName-logs.txt")
kubectl describe pod $PodName -n $Namespace | Out-File -Encoding utf8 -FilePath (Join-Path $EvidenceDir "$PodName-describe.txt")
kubectl get pod $PodName -n $Namespace -o yaml | Out-File -Encoding utf8 -FilePath (Join-Path $EvidenceDir "$PodName.yaml")

Write-Host "5. Killing pod $PodName ..."
kubectl delete pod $PodName -n $Namespace

$Elapsed = [math]::Round(((Get-Date) - $Start).TotalSeconds, 1)
Write-Host "Script runtime: $Elapsed seconds (first label to pod deleted). This is NOT MTTC."
Write-Host "MTTC = alert time to pod deleted. Note the alert time yourself and subtract it from the delete time."
# script-runtime.csv holds script runtimes only. Never average these with alert-to-delete MTTC figures.
"$((Get-Date).ToString('s')),$PodName,$Namespace,$Elapsed" | Out-File -Append -Encoding utf8 -FilePath (Join-Path $EvidenceDir "script-runtime.csv")
Write-Host "Done. Evidence saved in evidence\. Now rotate the exposed test secret by hand."
Write-Host "Do NOT commit evidence\ - it can contain secrets. See .gitignore."