#!/usr/bin/env python3

import logging

from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus, MaintenanceStatus

from loadbalancer_interface import LBConsumers


log = logging.getLogger(__name__)


class ProvidesOperatorCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.lb_consumers = LBConsumers(self, "lb-consumers")

        self.framework.observe(self.lb_consumers.on.requests_changed, self._provide_lbs)
        self.unit.status = ActiveStatus()

    def _provide_lbs(self, event):
        self.unit.status = MaintenanceStatus("processing requests")
        for request in self.lb_consumers.new_requests:
            response = request.response
            if not request.public:
                response.error = response.error_types.unsupported
                response.error_fields = {"public": "public only"}
            else:
                try:
                    response.address = self._create_lb(request)
                except Exception as e:
                    log.exception("Error creating load balancer")
                    response.error = response.error_types.provider_error
                    response.error_message = str(e)
            self.lb_consumers.send_response(request)
        self.unit.status = ActiveStatus()

    def _create_lb(self, request):
        return "dummy-lb"


if __name__ == "__main__":
    main(ProvidesOperatorCharm)
