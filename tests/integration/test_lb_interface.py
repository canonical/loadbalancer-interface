import logging

import pytest


log = logging.getLogger(__name__)


@pytest.mark.abort_on_fail
async def test_build_and_deploy(ops_test, lb_charms):
    lb_lib_path = await ops_test.build_lib(".")
    lb_charms._lb_lib_url = lb_lib_path
    charms: dict = await ops_test.build_charms(lb_charms.lb_provider)
    charms.update(
        **await ops_test.build_charms(
            lb_charms.lb_consumer,
            lb_charms.lb_provider_reactive,
            lb_charms.lb_consumer_reactive,
        )
    )

    bundle = ops_test.render_bundle("tests/integration/bundle.yaml", charms=charms)
    log.info("Deploying bundle")
    await ops_test.model.deploy(bundle)
    await ops_test.model.wait_for_idle(
        wait_for_active=True, raise_on_blocked=True, timeout=60 * 60
    )


async def test_failure(ops_test):
    def _check_blocked():
        for framework in ("", "-reactive"):
            unit = ops_test.model.applications[f"lb-consumer{framework}"].units[0]
            if unit.workload_status != "blocked":
                return False
        else:
            return True

    config = {"public": "false"}
    await ops_test.model.applications["lb-consumer"].set_config(config)
    await ops_test.model.applications["lb-consumer-reactive"].set_config(config)
    await ops_test.model.block_until(_check_blocked, timeout=2 * 60)
