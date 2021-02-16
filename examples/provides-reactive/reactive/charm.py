#!/usr/bin/env python3

from charms.reactive import when, endpoint_from_name
from charms import layer


@when("endpoint.lb-consumers.requests_changed")
def get_lb():
    lb_consumers = endpoint_from_name("lb-consumers")
    for request in lb_consumers.new_requests:
        response = request.response
        if request.public:
            response.error = response.error_types.unsupported
            response.error_fields = {"public": "internal only"}
        else:
            try:
                response.address = layer.my_charm.create_lb(request)
            except Exception as e:
                response.error = response.error_types.provider_error
                response.error_message = str(e)
        lb_consumers.send_response(request)
