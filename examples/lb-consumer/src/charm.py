#!/usr/bin/env python3

import logging
from subprocess import check_call

from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, WaitingStatus

from loadbalancer_interface import LBProvider


log = logging.getLogger(__name__)


class RequiresOperatorCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.lb_provider = LBProvider(self, "lb-provider")

        self.framework.observe(self.on.install, self._install)
        for event in (
            self.lb_provider.on.available,
            self.on.config_changed,
            self.on.leader_elected,
            self.on.upgrade_charm,
        ):
            self.framework.observe(event, self._request_lb)
        self._set_status()

    def _install(self, event):
        check_call(["apt-get", "update", "-yq"])
        check_call(["apt-get", "install", "nginx-full", "-y"])

    def _request_lb(self, event):
        if not (self.unit.is_leader() and self.lb_provider.is_available):
            return
        request = self.lb_provider.get_request("lb-consumer")
        request.protocol = request.protocols.tcp
        request.port_mapping = {80: 80}
        request.public = self.config["public"]
        self.lb_provider.send_request(request)

    def _set_status(self):
        if not self.lb_provider.is_available:
            self.unit.status = WaitingStatus("waiting on provider")
            return
        response = self.lb_provider.get_response("lb-consumer")
        if not response:
            self.unit.status = WaitingStatus("waiting on provider response")
            return
        if response.error:
            error = response.error_message or response.error_fields
            self.unit.status = BlockedStatus(f"LB failed: {error}")
            log.error(
                f"LB failed ({response.error}):\n"
                f"{response.error_message}\n"
                f"{response.error_fields}"
            )
            return
        self.unit.status = ActiveStatus(response.address)


if __name__ == "__main__":
    main(RequiresOperatorCharm)
