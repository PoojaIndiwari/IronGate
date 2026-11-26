# Signing contract — Person A + Person B (IronGate)

Fill this in with Person A in a 10-minute call, before you build anything.
If Person A is not ready, fill it in for your own test image and swap
their values in later — the policies do not change, only these values do.

- Registry + image name: YOUR-REGISTRY/paynest
  (example from the guide: 123456789.dkr.ecr.eu-west-1.amazonaws.com/paynest)
- Signing method: Cosign key (cosign.key / cosign.pub) — or keyless, with the OIDC issuer written here:
- Public key / issuer: _paste the public key here, or the issuer URL_
- Required for every deploy: valid Cosign signature + SLSA provenance attestation
- Banned: `:latest` tag, unsigned images, images from any other registry
- Person A name: ________  Person B name: ________  Date agreed: ________
