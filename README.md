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
loadbalancer_interface
```

## Usage

### Requesting Load Balancers

Requesting a load balancer from a provider is done via the `LBProvider` class.
The general pattern for using the class is:

  * Wait for the provider to become available
  * Get a `Request` object via the `get_request(name)` method
  * Set the appropriate fields on the request object
  * Send the `Request` via the `send_request(request)` method
  * Wait for the `Response` to be provided (or updated)
  * Get the `Response` object via either the `get_response(name)` method or
    via the `new_responses` property
  * Confirm that the request was successful and use the provided LB's address
  * Acknowledge the `Response` via `ack_response(response)`

There are examples in the docs on how to do this in [an operator charm](docs/examples/requires_operator.md)
or in [a reactive charm](docs/examples/requires_reactive.md).


### Providing Load Balancers

Providing a load balancer to consumers is done via the `LBConsumers` class.  The
general pattern for using the class is:

  * Wait for new or updated requests to come in
  * Iterate over each request object in the `new_requests` property
  * Create a load balancer according to the request's fields
  * Set the appropriate fields on the request's `response` object
  * Send the request's response via the `send_response(request)` method

There are examples in the docs on how to do this in [an operator charm](docs/examples/provides_operator.md)
or in [a reactive charm](docs/examples/provides_reactive.md).

## API Reference

See [the docs](docs/api.md) for detailed reference on the API.


<!-- Links -->

[Operator Framework]: https://github.com/canonical/operator/
[charms.reactive Framework]: https://charmsreactive.readthedocs.io/
