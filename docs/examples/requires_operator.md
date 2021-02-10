# Operator Framework Requires Charm Example

## `metadata.yaml`

```yaml
requires:  # consumes a LB from a provider
  lb-provider:
    interface: loadbalancer
    limit: 1  # only supports a single LB provider per relation endpoint
```

## `src/charm.py`

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
        request.protocol = request.protocols.https
        request.port_mapping = {443: 443}
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
