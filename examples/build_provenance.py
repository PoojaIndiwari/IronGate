"""Emit the SLSA v1 predicate for the reviewed GitHub Actions build."""
import json
import os
import sys


def predicate(env):
    repo = "https://github.com/" + env["GITHUB_REPOSITORY"]
    workflow = "https://github.com/" + env["GITHUB_WORKFLOW_REF"]
    revision = env["GITHUB_SHA"]
    base_name, base_hash = env["BASE_IMAGE"].split("@sha256:")
    return {
        "buildDefinition": {
            "buildType": repo + "/blob/main/docs/build-type.md",
            "externalParameters": {
                "source": repo,
                "ref": env["GITHUB_REF"],
                "revision": revision,
                "platform": "linux/amd64",
            },
            "resolvedDependencies": [
                {"uri": "git+" + repo, "digest": {"gitCommit": revision}},
                {"uri": "docker://docker.io/library/" + base_name, "digest": {"sha256": base_hash}},
            ],
        },
        "runDetails": {
            "builder": {"id": workflow},
            "metadata": {
                "invocationId": (
                    f'{repo}/actions/runs/{env["GITHUB_RUN_ID"]}/attempts/{env["GITHUB_RUN_ATTEMPT"]}'
                )
            },
        },
    }


if __name__ == "__main__":
    json.dump(predicate(os.environ), sys.stdout, indent=2)
