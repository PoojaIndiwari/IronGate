# Signing contract — Person A + Person B (IronGate)

Agreed contract between Person A (pipeline & artifacts) and Person B (runtime admission & detection).
Enforced by `runtime/proof-policy.yaml.in` (rendered to `local-output/admission.yaml`) and verified with `examples/verify.sh`.

- **Registry + image name:** `ghcr.io/poojaindiwari/irongate` (deployed by immutable `@sha256:` digest)
- **Verified release digest:** `ghcr.io/poojaindiwari/irongate@sha256:19c63ca7bc3b224f95b925c1970cfb15c409fd45889e83f51fa20bbc113b5156`
- **Signing method:** Cosign keyless (Sigstore Fulcio + Rekor transparency log `https://rekor.sigstore.dev`)
- **OIDC issuer:** `https://token.actions.githubusercontent.com`
- **Certificate identity (signer):** `https://github.com/PoojaIndiwari/IronGate/.github/workflows/release.yml@refs/heads/main`
- **Required for every deploy:** valid Cosign signature + signed SLSA v1 provenance attestation (`https://slsa.dev/provenance/v1`) + signed SPDX SBOM attestation (`https://spdx.dev/Document`)
- **Banned:** `:latest` tag, mutable tags, unsigned images, images from any other registry, privileged pods
- **Namespaces:** `paynest-demo` (signed release deploy) and `paynest` (runtime policy & containment tests)
- **Date verified:** `2026-11-27`
