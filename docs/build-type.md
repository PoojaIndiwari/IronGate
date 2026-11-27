# PayNest container build

The reviewed release workflow checks out the GitHub event commit and uses its
Dockerfile to build a single Linux/amd64 image. It takes the source repository,
ref, commit and platform as external parameters. It reads the Python base image
from the Dockerfile and supplies the commit time as SOURCE_DATE_EPOCH. Buildx
pushes the image and returns the registry digest. The release job scans that
digest and signs it only when its required jobs succeed.

The signing job constructs SLSA v1 provenance from trusted workflow context
and the build job's outputs. Cosign wraps that predicate in an in-toto statement
whose subject is the built image digest. This teaching build makes no certified
SLSA level claim. When upgrading the builder, record the exact BuildKit image,
Buildx version, base digest and Git commit in the reproducibility experiment.
