# PayNest signing contract

IronGate uses this contract to decide which PayNest releases may run in the
`paynest-demo` Kubernetes namespace. Person A builds and signs the release.
Person B verifies the image signature, build provenance, and SBOM, then tests
the cluster’s admission decision.

## Agreed release requirements

| Field | Agreed value |
| --- | --- |
| GitHub repository | `PoojaIndiwari/IronGate` |
| Current image repository | `ghcr.io/poojaindiwari/irongate` |
| Accepted image reference | `ghcr.io/poojaindiwari/irongate@sha256:` followed by the full 64-character digest |
| Certificate issuer | `https://token.actions.githubusercontent.com` |
| Certificate identity | `https://github.com/PoojaIndiwari/IronGate/.github/workflows/release.yml@refs/heads/main` |
| Build provenance type | `https://slsa.dev/provenance/v1` |
| SBOM type | `https://spdx.dev/Document` |
| Platform | `linux/amd64` |
| Enforcement scope | `paynest-demo` namespace |
| Admission requirement | Require the approved repository, an immutable digest, a trusted signature, and both signed attestations. Deny verification errors. |

The team plans to use AWS ECR for the final cloud release. This record covers
the GitHub Container Registry release. Any change to the trusted repository or
signer requires peer review.

## Release evidence — e4ed8b9

| Field | Recorded value |
| --- | --- |
| Git commit | `e4ed8b9733ca55f1b0f113bd1ffc31587379424d` |
| Signed image | `ghcr.io/poojaindiwari/irongate@sha256:19c63ca7bc3b224f95b925c1970cfb15c409fd45889e83f51fa20bbc113b5156` |
| Successful CD run |https://github.com/PoojaIndiwari/IronGate/actions/runs/45952676755|
| Earlier CD run blocked by Trivy |https://github.com/PoojaIndiwari/IronGate/actions/runs/45949243505|

## Verification and admission results reported by Person B

| Test | Status | Evidence |
| --- | --- | --- |
| Image signature | Passed | Cosign verified the signed image digest against the agreed certificate identity and issuer. |
| Build provenance | Passed | The signed SLSA v1 attestation identified the IronGate repository, `refs/heads/main`, and the release workflow on `main`. |
| Software bill of materials | Passed | The signed SPDX 2.3 attestation listed 31 packages. |
| Deployment of approved digest | Passed | The `paynest` and `proof-check` Pods were both `1/1` and Running in `paynest-demo`. The PayNest service on port `8080` returned `{"status":"ok"}` from `/health`. |
| Tag-only image | Denied as expected | `proof-check-unsigned` used `ghcr.io/poojaindiwari/irongate:latest`. Policy `irongate-source` denied it with the message “PayNest requires the approved repository and an immutable SHA-256 digest.” |
| Unsigned image referenced by digest | Pending | Use a distinct, existing unsigned digest from the approved repository. Record the policy name and its signature-verification denial. |
| Missing attestation, wrong signer, or unapproved registry | Pending | Record a separate admission result for each case when tested. |