#!/usr/bin/env python3

import logging

from ops.charm import CharmBase
from ops.model import ActiveStatus, BlockedStatus

from loadbalancer_interface import LBProvider


log = logging.getLogger(__name__)


class RequiresOperatorCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.lb_provider = LBProvider(self, "lb-provider")

        self.framework.observe(self.lb_provider.on.available, self._request_lb)
        self.framework.observe(self.lb_provider.on.responses_changed, self._get_lb)

    def _request_lb(self, event):
        request = self.lb_provider.get_request("my-service")
        request.protocol = request.protocols.https
        request.port_mapping = {443: 443}
        request.public = self.config["public"]
        self.lb_provider.send_request(request)

    def _get_lb(self, event):
        response = self.lb_provider.get_response("my-service")
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
        self.unit.status = ActiveStatus()
