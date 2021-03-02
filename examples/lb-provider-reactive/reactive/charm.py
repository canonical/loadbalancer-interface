#!/usr/bin/env python3

from charms.reactive import when, when_not, set_flag, endpoint_from_name
from charms import layer


@when_not("charm.status.is-set")
def set_status():
    layer.status.active("")
    set_flag("charm.status.is-set")


@when("endpoint.lb-consumers.requests_changed")
def get_lb():
    layer.status.maintenance("processing requests")
    lb_consumers = endpoint_from_name("lb-consumers")
    for request in lb_consumers.new_requests:
        response = request.response
        if not request.public:
            response.error = response.error_types.unsupported
            response.error_fields = {"public": "public only"}
        else:
            try:
                response.address = layer.provides_reactive.create_lb(request)
            except Exception as e:
                response.error = response.error_types.provider_error
                response.error_message = str(e)
        lb_consumers.send_response(request)
    layer.status.active("")
