#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 2 ]]; then
  echo "Usage: bash examples/verify.sh REGISTRY/IMAGE@sha256:DIGEST WORKFLOW_CERTIFICATE_IDENTITY" >&2
  exit 2
fi
image=$1
identity=$2
[[ "$image" =~ @sha256:[0-9a-f]{64}$ ]]
trust=(--certificate-identity "$identity" --certificate-oidc-issuer https://token.actions.githubusercontent.com)
cosign verify "${trust[@]}" "$image"
cosign verify-attestation "${trust[@]}" --type slsaprovenance1 "$image"
cosign verify-attestation "${trust[@]}" --type spdxjson "$image"
