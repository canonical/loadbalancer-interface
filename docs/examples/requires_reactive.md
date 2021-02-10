# charms.reactive Framework Requires Charm Example

## `metadata.yaml`

```yaml
requires:  # consumes a LB from a provider
  lb-provider:
    interface: loadbalancer
    limit: 1  # only supports a single LB provider per relation endpoint
```

## `src/charm.py`

```python
from charms.reactive import when, endpoint_from_name
from charmhelpers.core import hookenv
from charms import layer


@when('endpoint.lb-provider.available')
def request_lb():
    lb_provider = endpoint_from_name('lb-provider')
    lb_provider.get_request('my-service')
    request.traffic_type = 'https'
    request.port_mapping = {443: 443}
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
