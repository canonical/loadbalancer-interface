#!/usr/bin/env python3

import logging

from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, MaintenanceStatus, WaitingStatus

from loadbalancer_interface import LBProvider


log = logging.getLogger(__name__)


class RequiresOperatorCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.lb_provider = LBProvider(self, "lb-provider")

        if not self.lb_provider.is_available:
            self.unit.status = WaitingStatus("waiting on provider")

        self.framework.observe(self.lb_provider.on.available, self._request_lb)
        self.framework.observe(self.lb_provider.on.response_changed, self._get_lb)
        if self.lb_provider.is_available:
            self.framework.observe(self.on.config_changed, self._request_lb)

    def _request_lb(self, event):
        self.unit.status = MaintenanceStatus("sending request")
        request = self.lb_provider.get_request("my-service")
        request.protocol = request.protocols.https
        request.port_mapping = {443: 443}
        request.public = self.config["public"]
        self.lb_provider.send_request(request)
        self.unit.status = WaitingStatus("waiting on provider response")

    def _get_lb(self, event):
        response = self.lb_provider.get_response("my-service")
        if not response:
            return
        if response.error:
            self.unit.status = BlockedStatus(f"LB failed: {response.error}")
            log.error(
                f"LB failed ({response.error}):\n"
                f"{response.error_message}\n"
                f"{response.error_fields}"
            )
            return
        log.info(f"LB is available at {response.address}")
        self.lb_provider.ack_response(response)
        self.unit.status = ActiveStatus(response.address)


if __name__ == "__main__":
    main(RequiresOperatorCharm)
