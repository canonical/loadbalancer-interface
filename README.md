# `loadbalancer` Interface Protocol API Library

This library provides an API for requesting and providing load balancers or
ingress endpoints from one charm to another. It can be used in either charms
written in the newer [Operator Framework][] or older charms still using the
[charms.reactive Framework][].


## Installation / Setup

Include this library as a dependency for your charm, either in
`requirements.txt` for Operator Framework charms, or `wheelhouse.txt` for
reactive charms:

```
# TODO: publish this to PyPI
https://github.com/juju-solutions/loadbalancer-interface/archive/master.zip#egg=loadbalancer_interface
```

Then define a relation endpoint which uses the `loadbalancer` interface protocol
in your charm's `metadata.yaml`, under either `requires` or `provides`:

```yaml
requires:  # consumes a LB from a provider
  lb-provider:
    interface: loadbalancer
    limit: 1  # only supports a single LB provider per relation endpoint
provides:  # provides LBs to consumers
  lb-consumers:
    interface: loadbalancer
```

## Requesting Load Balancers

Requesting a load balancer from a provider is done via the `LBProvider` class.
The general pattern for using the class is:

  * Wait for the provider to become available
  * Get a request object via the `get_request(name)` method
  * Set the appropriate fields on the request object
  * Send the request via the `send_request(request)` method
  * Wait for the response to be provided (or updated)
  * Get the response object via either the `get_response(name)` method or
    via the `new_responses` property
  * Confirm that the request was successful and use the provided LB's address
  * Acknowledge the response via `ack_response(response)`

### Example: Operator charm

For Operator Framework charms, you will use the normal pattern for associating
an instance of the `LBProvider` class with the relation endpoint and interacting
with it via events:

```python
import logging

from ops.charm import CharmBase
from ops.model import ActiveStatus, BlockedStatus

from loadbalancer_interface import LBProvider


log = logging.getLogger(__name__)


class MyCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.lb_provider = LBProvider(self, 'lb-provider')

        self.framework.observe(self.lb_provider.on.available, self._request_lb)
        self.framework.observe(self.lb_provider.on.responses_changed, self._get_lb)

    def _request_lb(self, event):
        request = self.lb_provider.get_request('my-service')
        request.traffic_type = 'https'
        request.backend_ports = [443]
        self.lb_provider.send_request(request)

    def _get_lb(self, event):
        response = self.lb_provider.get_response('my-service')
        if not response.success:
            self.unit.status = BlockedStatus(response.message)
            return
        log.info(f'LB is available at {response.address}')
        self.lb_provider.ack_response(response)
        self.unit.status = ActiveStatus()
```

### Example: Reactive charm

For charms using charms.reactive, the following flags will be managed
automatically:

  * `endpoint.{endpoint_name}.available` Set when a provider is available, or
    cleared when not.
  * `endpoint.{endpoint_name}.responses_changed` Set when a response comes in or
    is updated, cleared when all responses have been acknowledged.

Then, the instances will be available via `endpoint_from_name(relation_endpoint)` or
`endpoint_from_flag(flag)` in the same way as normal interface layers:

```python
from charms.reactive import when, endpoint_from_name
from charmhelpers.core import hookenv
from charms import layer


@when('endpoint.lb-provider.available')
def request_lb():
    lb_provider = endpoint_from_name('lb-provider')
    lb_provider.get_request('my-service')
    request.traffic_type = 'https'
    request.backend_ports = [443]
    lb_provider.send_request(request)


@when('endpoint.lb-provider.responses_changed')
def get_lb():
    lb_provider = endpoint_from_name('lb-provider')
    response = lb_provider.get_response('my-service')
    if not response.success:
        layer.status.blocked(response.message)
        return
    hookenv.log(f'LB is available at {response.address}')
    lb_provider.ack_response(response)
    layer.status.active()
```

## Providing Load Balancers

Providing a load balancer to consumers is done via the `LBConsumers` class.  The
general pattern for using the class is:

  * Wait for new or updated requests to come in
  * Iterate over each request object in the `new_requests` property
  * Create a load balancer according to the request's fields
  * Set the appropriate fields on the request's `response` object
  * Send the request's response via the `send_response(request)` method

### Example: Operator charm

For Operator Framework charms, you will use the normal pattern for associating
an instance of the `LBConsumers` class with the relation endpoint and interacting
with it via events:

```python
import logging

from ops.charm import CharmBase
from ops.model import ActiveStatus, BlockedStatus

from loadbalancer_interface import LBConsumers


log = logging.getLogger(__name__)


class MyCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.lb_consumers = LBConsumers(self, 'lb-consumers')

        self.framework.observe(self.lb_consumers.on.requests_changed,
                               self._provide_lbs)

    def _provide_lbs(self, event):
        for request in self.lb_consumers.new_requests:
            try:
                request.response.address = self._create_lb(request)
                request.response.success = True
            except LBError as e:
                request.response.success = False
                request.response.message = e.message
            self.lb_consumers.send_response(request)
```

### Example: Reactive charm

For charms using charms.reactive, the following flags will be managed
automatically:

  * `endpoint.{endpoint_name}.requests_changed` Set when a request comes in or
    is updated, cleared when all requests have been responded to.

Then, the instances will be available via `endpoint_from_name(relation_endpoint)` or
`endpoint_from_flag(flag)` in the same way as normal interface layers:

```python
from charms.reactive import when, endpoint_from_name
from charms import layer


@when('endpoint.lb-consumers.requests_changed')
def get_lb():
    lb_consumers = endpoint_from_name('lb-consumers')
    for request in lb_consumers.new_requests:
        try:
            request.response.address = layer.my_charm.create_lb(request)
            request.response.success = True
        except LBError as e:
            request.response.success = False
            request.response.message = e.message
        lb_consumers.send_response(request)
```
