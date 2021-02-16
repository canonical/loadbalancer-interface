#!/usr/bin/env python3

from charms.reactive import when, endpoint_from_name
from charmhelpers.core import hookenv
from charms import layer


@when("endpoint.lb-provider.available")
def request_lb():
    lb_provider = endpoint_from_name("lb-provider")
    request = lb_provider.get_request("my-service")
    request.protocol = request.protocols.https
    request.port_mapping = {443: 443}
    lb_provider.send_request(request)


@when("endpoint.lb-provider.responses_changed")
def get_lb():
    lb_provider = endpoint_from_name("lb-provider")
    response = lb_provider.get_response("my-service")
    if response.error:
        layer.status.blocked(f"LB failed: {response.error}")
        hookenv.log(
            f"LB failed ({response.error}):\n"
            f"{response.error_message}\n"
            f"{response.error_fields}",
            hookenv.ERROR,
        )
        return
    hookenv.log(f"LB is available at {response.address}")
    lb_provider.ack_response(response)
    layer.status.active()
