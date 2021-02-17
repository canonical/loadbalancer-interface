# API Reference

## Table of Contents

  * [`LBProvider` Class](#lbprovider-class)
  * [`LBConsumers` Class](#lbconsumers-class)
  * [`Request` Objects](#request-objects)
  * [`HealthCheck` Objects](#healthcheck-objects)
  * [`Response` Objects](#response-objects)

-----------------------------------------

## `LBProvider` Class

This is the main API class for requesting load balancers from a provider charm.
When instantiated, it should be passed a charm instance and a relation name.

### Events

  * `available` Emitted once the provider is available to take requests
  * `response_available` Emitted the first time a complete response becomes available
  * `response_changed` Emitted whenever one or more responses have been received or updated

### Methods

  * `get_request(name)` Get or create a request with the given name
  * `send_request(request)` Send the completed request to the provider
  * `get_response(name)` Get the response to a specific request (equivalent to `get_request(name).response`)
  * `ack_response(response)` Acknowledge a response so that it is no longer considered new or changed

### Properties

  * `is_available` Whether the provider is available to take requests
  * `is_changed` Whether there are any new or changed responses which have not been acknowledged
  * `has_response` Whether there is at least one complete response available
  * `all_responses` A list of all received responses
  * `complete_responses` A list of all up to date received responses, even if they have not changed
  * `new_responses` A list of all complete responses which are new or have changed and not been acknowledged

### Flags

For charms using the older charms.reactive framework, the following flags will
be automatically managed:

  * `endpoint.{relation_name}.available` Set or cleared based on `is_available`
  * `endpoint.{relation_name}.response.available` Set or cleared based on `has_response`
  * `endpoint.{relation_name}.response.changed` Set or cleared based on `is_changed`


## `LBConsumers` Class

This is the main API class for providing load balancers to consumer charms.
When instantiated, it should be passed a charm instance and a relation name.

### Events

  * `requests_changed` Emitted whenever one or more requests have been received or updated

### Methods

  * `send_response(request)` Send the completed `Response` attached to the given `Request`

### Properties

  * `is_changed` Whether there are any new or changed requests which have not been responded to
  * `all_requests` A list of all received requests, even if they have not changed
  * `new_requests` A list of all requests which are new or have changed and not been responded to

### Flags

For charms using the older charms.reactive framework, the following flags will
be automatically managed:

  * `endpoint.{relation_name}.requests_changed` Set or cleared based on `is_changed`


## `Request` Objects

Represents a request for a load balancer.

Acquired from `LBProvider.get_request(name)`, `LBConsumers.all_requests`, or `LBConsumers.new_requests`.

### Class Attributes

  * `protocols` An Enum of possible values for the Request or HealthCheck `protocol` field.
    Can be one of:
    * `protocols.tcp`
    * `protocols.udp`
    * `protocols.http`
    * `protocols.https`

### Properties

  * `name` Name of the request (`str`, read-only)
  * `response` `Reponse` to this request (will always exist, but may be "empty"; see below)
  * `hash` An MD5 hash of the data for the request (`str`, read-only)

### Fields

  * `protocol` Type of traffic to route (`Request.protocols`, required)
  * `backends` List of backend addresses (`str`s, default: every units' `ingress-address`)
  * `port_mapping` Mapping of ingress ports to backend ports (`dict[int -> int]`, required)
  * `algorithm` List of traffic distribution algorithms, in order of preference (`str`s, optional)
  * `sticky` Whether traffic "sticks" to a given backend (`bool`, default: `False`)
  * `health_checks` List of `HealthCheck` objects (see below, optional)
  * `public` Whether the address should be public (`bool`, default: `True`)
  * `tls_termination` Whether to enable TLS termination (`bool`, default: `False`)
  * `tls_cert` If TLS termination is enabled, a manually provided cert (`str`, optional)
  * `tls_key` If TLS termination is enabled, a manually provided key (`str`, optional)
  * `ingress_address` A manually provided ingress address (optional, may not be supported)

### Methods

  * `add_health_check(**fields)` Create a `HealthCheck` object (see below) with the given fields and add it to the list.


## `HealthCheck` Objects

Represents a health check endpoint to determine if a backend is functional.

Acquired from `Request.add_health_check()`, or `Request.health_checks`.

### Fields

  * `protocol` Type of traffic to use to make the check (e.g., "https", "udp", etc.) (`Request.protocols`, required)
  * `port` Port to check on (`int`, required)
  * `path` Path on the backend to check (e.g., for "https" or "http" types) (`str`, optional)
  * `interval` How many seconds to wait between checks (`int`, default: 30)
  * `retries` How many failed attempts before considering a backend down (`int`, default: 3)


## `Response` Objects

Represents a response to a load balancer request.

Acquired from `Request.response`.  A `Request` object will always have a
`response` attribute, but the response might be "empty" if it has not been
filled in with valid data, in which case `bool(response)` will be `False`.

### Class Attributes

  * `error_types` An Enum of possible values for the `error_type` field.  Can be one of:
    * `error_types.unsupported`
    * `error_types.provider_error`

### Properties

  * `name` Name of the request (`str`, read-only)
  * `hash` An MD5 hash of the data for the request (read-only)

### Fields

  * `address` The address of the LB (`str`, required if `error` is `None`)
  * `error` Whether the request was successful (`Response.error_types`, default: `None`)
  * `error_message` General info about failure (`str`, default: None)
  * `error_fields` Mapping of request field names to error messages (`dict[str,str]`, default: `{}`)
  * `request_hash` The hash of the `Request` when this `Response` was sent (`str`, set automatically)

At least one of `error_message` or `error_fields` are required if `error` is not `None`.
