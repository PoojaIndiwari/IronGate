package main

import rego.v1

podspec := input.spec if input.kind == "Pod"

podspec := input.spec.template.spec if input.kind == "Deployment"

deny contains msg if {
    some container in podspec.containers
    security := object.get(container, "securityContext", {})
    object.get(security, "allowPrivilegeEscalation", true) != false
    msg := sprintf("%s must set allowPrivilegeEscalation to false", [container.name])
}
