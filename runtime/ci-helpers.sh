#!/usr/bin/env bash
# Shared helpers for .github/workflows/person-b-runtime.yml. Source it: `source runtime/ci-helpers.sh`.
set -euo pipefail

# Versions are pinned here. Each download is checked against the checksum file the
# project publishes next to the binary (kind, kubectl, helm all do).
KIND_VERSION="${KIND_VERSION:-v0.33.0}"
KUBECTL_VERSION="${KUBECTL_VERSION:-v1.37.0}"
HELM_VERSION="${HELM_VERSION:-v4.3.2}"
KYVERNO_APP_LINE="${KYVERNO_APP_LINE:-1.20}"   # the Kyverno line the policies were proven on

install_tools() {
  local tmp; tmp="$(mktemp -d)"
  curl -fsSL -o "$tmp/kind" "https://kind.sigs.k8s.io/dl/${KIND_VERSION}/kind-linux-amd64"
  curl -fsSL -o "$tmp/kind.sha256sum" "https://kind.sigs.k8s.io/dl/${KIND_VERSION}/kind-linux-amd64.sha256sum"
  echo "$(cut -d' ' -f1 "$tmp/kind.sha256sum")  $tmp/kind" | sha256sum -c -

  curl -fsSL -o "$tmp/kubectl" "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl"
  curl -fsSL -o "$tmp/kubectl.sha256" "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl.sha256"
  echo "$(cut -d' ' -f1 "$tmp/kubectl.sha256")  $tmp/kubectl" | sha256sum -c -

  curl -fsSL -o "$tmp/helm.tgz" "https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz"
  curl -fsSL -o "$tmp/helm.sha256sum" "https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz.sha256sum"
  echo "$(cut -d' ' -f1 "$tmp/helm.sha256sum")  $tmp/helm.tgz" | sha256sum -c -
  tar -xzf "$tmp/helm.tgz" -C "$tmp"

  sudo install -m 0755 "$tmp/kind" /usr/local/bin/kind
  sudo install -m 0755 "$tmp/kubectl" /usr/local/bin/kubectl
  sudo install -m 0755 "$tmp/linux-amd64/helm" /usr/local/bin/helm
  kind version; kubectl version --client; helm version --short
}

# Install the newest Kyverno chart whose app version is on KYVERNO_APP_LINE, and record which one.
install_kyverno() {
  helm repo add kyverno https://kyverno.github.io/kyverno/ >/dev/null
  helm repo update >/dev/null
  local chart
  chart="$(helm search repo kyverno/kyverno --versions -o json \
    | jq -r --arg line "$KYVERNO_APP_LINE" \
        '[.[] | select(.name == "kyverno/kyverno") | select(.app_version | test("^v?" + ($line | gsub("\\."; "\\.")) + "\\.[0-9]+$"))][0].version // empty')"
  if [[ -z "$chart" ]]; then
    echo "::error::No Kyverno chart found for app version line ${KYVERNO_APP_LINE}.x"; return 1
  fi
  echo "Installing Kyverno chart ${chart} (app line ${KYVERNO_APP_LINE}.x)"
  helm install kyverno kyverno/kyverno --version "$chart" -n security --create-namespace --wait --timeout 5m
  kubectl rollout status deployment/kyverno-admission-controller -n security --timeout=120s
  # Wait for kyverno-svc endpoints so policy-validation webhook calls do not race kube-proxy.
  for _ in $(seq 1 20); do
    if [[ -n "$(kubectl get endpoints kyverno-svc -n security -o jsonpath='{.subsets[0].addresses[0].ip}' 2>/dev/null || true)" ]]; then
      break
    fi
    sleep 2
  done
  echo "- Kyverno chart: \`${chart}\`" >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
}

# apply_retry FILE: retry kubectl apply briefly in case Kyverno's policy webhook is still warming up.
apply_retry() {
  local file="$1"
  for i in $(seq 1 10); do
    if kubectl apply -f "$file"; then
      return 0
    fi
    echo "Retrying kubectl apply -f $file ($i/10)..."
    sleep 3
  done
  kubectl apply -f "$file"
}

# wait_ready KIND NAME [SECONDS]: poll readiness instead of sleeping and hoping.
# Kyverno policies.kyverno.io/v1 reports .status.conditionStatus.ready (older CRDs use .status.ready).
wait_ready() {
  local kind="$1" name="$2" limit="${3:-120}" waited=0 ready=""
  while :; do
    ready="$(kubectl get "$kind" "$name" -o jsonpath='{.status.conditionStatus.ready}{.status.ready}' 2>/dev/null || true)"
    if [[ "$ready" == *true* ]]; then
      echo "$kind/$name is ready"
      return 0
    fi
    if (( waited >= limit )); then
      echo "::error::$kind/$name was not ready after ${limit}s"; kubectl get "$kind" "$name" -o yaml || true; return 1
    fi
    sleep 3; waited=$((waited + 3))
  done
}

# expect_denied FILE EXPECTED_TEXT [kubectl apply args...]
# Passes only if the apply is rejected AND the rejection message contains EXPECTED_TEXT,
# so an unrelated failure (typo, quota, another policy) cannot turn the check green.
# EXPECTED_TEXT may list alternatives separated by "||" for cases where two admission
# layers can both deny and the API server reports whichever answers first.
expect_denied() {
  local file="$1" expected="$2"; shift 2
  local out
  if out="$(kubectl apply -f "$file" "$@" 2>&1)"; then
    echo "::error::FAIL: $file was admitted but should have been denied"; echo "$out"
    kubectl delete -f "$file" --ignore-not-found >/dev/null 2>&1 || true
    return 1
  fi
  local alt found=0 IFS=$'\n'
  for alt in $(sed 's/||/\n/g' <<<"$expected"); do
    if grep -qiF -- "$alt" <<<"$out"; then found=1; break; fi
  done
  if (( found )); then
    echo "PASS: $file denied with the expected reason: $expected"
  else
    echo "::error::FAIL: $file was denied, but not for the expected reason"
    echo "expected to contain: $expected"; echo "$out"; return 1
  fi
}
