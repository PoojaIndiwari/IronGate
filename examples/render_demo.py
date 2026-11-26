"""Render the two teammates' agreed repository and digest into local manifests."""
import argparse
import re
from pathlib import Path


def render(repository, image, project):
    if not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+", repository):
        raise ValueError("Use the GitHub OWNER/REPO form, including its original case")
    if not re.fullmatch(r"[a-z0-9.-]+/[a-z0-9._/-]+@sha256:[0-9a-f]{64}", image):
        raise ValueError("Use the full lowercase registry image followed by @sha256: and 64 hex digits")
    image_path = image.split("@")[0]
    source = "https://github.com/" + repository
    signer = source + "/.github/workflows/release.yml@refs/heads/main"
    policy = (project / "runtime/proof-policy.yaml.in").read_text()
    for key, value in {
        "__IMAGE_PATTERN__": image_path.replace(".", "[.]"),
        "__IMAGE__": image_path,
        "__SOURCE__": source,
        "__SIGNER__": signer,
    }.items():
        policy = policy.replace(key, value)
    workload = (project / "k8s/dev/paynest.yaml").read_text()
    workload = workload.replace("paynest-dev", "paynest-demo").replace("paynest:week1", image)
    destination = project / "local-output"
    destination.mkdir(exist_ok=True)
    (destination / "admission.yaml").write_text(policy)
    (destination / "release.yaml").write_text(workload)
    namespace = (project / "k8s/dev/namespace.yaml").read_text()
    (destination / "namespace.yaml").write_text(namespace.replace("paynest-dev", "paynest-demo"))
    pod = (project / "runtime/check-pod.yaml.in").read_text().replace("__FULL_IMAGE__", image)
    (destination / "check-pod.yaml").write_text(pod)
    client = pod.replace("name: proof-check", "name: health-client").replace("namespace: paynest-demo", "namespace: paynest-test")
    client = client.replace("    app: paynest", "    role: health-client")
    (destination / "health-client.yaml").write_text(client)
    print(f"Prepared namespace, admission, release, check-pod and health-client YAML in {destination.name}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("repository", help="GitHub OWNER/REPO, as it appears in the certificate")
    parser.add_argument("image", help="Registry image including its sha256 digest")
    args = parser.parse_args()
    try:
        render(args.repository, args.image, Path(__file__).resolve().parents[1])
    except ValueError as error:
        parser.error(str(error))
