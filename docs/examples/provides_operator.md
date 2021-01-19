# Operator Framework Provides Charm Example

## `metadata.yaml`

```yaml
provides:  # provides LBs to consumers
  lb-consumers:
    interface: loadbalancer
```

## `src/charm.py`

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
