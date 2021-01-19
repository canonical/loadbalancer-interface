# charms.reactive Framework Provides Charm Example

## `metadata.yaml`

```yaml
provides:  # provides LBs to consumers
  lb-consumers:
    interface: loadbalancer
```

## `reactive/my_charm.py`

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
