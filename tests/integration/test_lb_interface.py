import logging

import pytest
from pytest_operator import OperatorTest


log = logging.getLogger(__name__)


@pytest.mark.lb_charms
class LBIntegrationTest(OperatorTest):
    @pytest.mark.abort_on_fail
    async def test_build_and_deploy(self):
        lb_lib_path = await self.build_lib(".")
        self.lb_lib_url = f"file://{lb_lib_path}#egg=loadbalancer_interface"
        bundle = self.render_bundle(
            "tests/integration/bundle.yaml",
            charms=await self.build_charms(
                self.lb_charms.lb_provider,
                self.lb_charms.lb_consumer,
                self.lb_charms.lb_provider_reactive,
                self.lb_charms.lb_consumer_reactive,
            ),
        )
        log.info("Deploying bundle")
        await self.model.deploy(bundle)
        await self.model.wait_for_idle(
            wait_for_active=True, raise_on_blocked=True, timeout=60 * 60
        )

    def _check_blocked(self):
        for framework in ("", "-reactive"):
            unit = self.model.applications[f"lb-consumer{framework}"].units[0]
            if unit.workload_status != "blocked":
                return False
        else:
            return True

    async def test_failure(self):
        config = {"public": "false"}
        await self.model.applications["lb-consumer"].set_config(config)
        await self.model.applications["lb-consumer-reactive"].set_config(config)
        await self.model.block_until(self._check_blocked, timeout=2 * 60)
