import logging
from pathlib import Path

import pytest
from pytest_operator import OperatorTest


log = logging.getLogger(__name__)


class LBIntegrationTest(OperatorTest):
    setup_passed = False

    async def test_build_and_deploy(self):
        lib_path = await self.build_lib(".")
        charm_paths = self.render_charms(
            *Path("examples").glob("*"),
            include=["wheelhouse.txt", "requirements.txt"],
            lib_path=lib_path,
        )
        bundle = self.render_bundle(
            "tests/integration/bundle.yaml",
            charms=await self.build_charms(*charm_paths),
        )
        log.info("Deploying bundle")
        await self.model.deploy(bundle)
        await self.model.wait_for_idle(
            wait_for_active=True, raise_on_blocked=True, timeout=60 * 60
        )
        type(self).setup_passed = True

    def _check_blocked(self):
        for framework in ("operator", "reactive"):
            unit = self.model.applications[f"requires-{framework}"].units[0]
            if unit.workload_status != "blocked":
                return False
        else:
            return True

    async def test_failure(self):
        if not self.setup_passed:
            pytest.xfail("Initial deploy failed")
        config = {"public": "true"}
        await self.model.applications["requires-operator"].set_config(config)
        await self.model.applications["requires-reactive"].set_config(config)
        await self.model.block_until(self._check_blocked, timeout=2 * 60)
