package main

import rego.v1

requires_imdsv2(instance) if {
    some options in instance.metadata_options
    options.http_tokens == "required"
}

deny contains msg if {
    some change in input.resource_changes
    change.type == "aws_instance"
    after := change.change.after
    after != null
    not requires_imdsv2(after)
    msg := sprintf("%s must require IMDSv2", [change.address])
}
