#!/usr/bin/env python3

from charms.reactive import set_flag, clear_flag, when, when_not, endpoint_from_name
from charmhelpers.core import hookenv
from charms import layer


@when("endpoint.lb-provider.joined")
@when_not("endpoint.lb-provider.available")
def waiting():
    layer.status.waiting("waiting for provider")


@when("endpoint.lb-provider.available")
@when_not("charm.request.sent")
def request_lb():
    layer.status.maintenance("sending request")
    lb_provider = endpoint_from_name("lb-provider")
    request = lb_provider.get_request("my-service")
    request.protocol = request.protocols.https
    request.port_mapping = {443: 443}
    request.public = hookenv.config("public")
    lb_provider.send_request(request)
    set_flag("charm.request.sent")


@when("charm.request.sent")
@when_not("endpoint.lb-provider.response.available")
def waiting_for_response():
    layer.status.waiting("waiting for provider repsonse")


@when("charm.request.sent")
@when("config.changed.public")
def update_request():
    clear_flag("charm.request.sent")
    clear_flag("config.changed.public")


@when("endpoint.lb-provider.response.changed")
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
    layer.status.active(response.address)
