from contextlib import contextmanager
from pathlib import Path
import shutil

import pytest


try:
    from importlib.resources import path as resource_path
except ImportError:
    # Shims for importlib_resources and pkg_resources to behave like the stdlib
    # version from 3.7+.
    try:
        from importlib_resources import path as resource_path
    except ImportError:
        from pkg_resources import resource_filename

        @contextmanager
        def resource_path(package, resource):
            rf = resource_filename(package, resource)
            yield Path(rf)


@pytest.fixture(scope="module")
def lb_charms(ops_test):
    """Fixture which provides the load balancer example charms for testing.

    This fixture returns an object with the following attributes:

      * lb_provider - A charm which provides loadbalancers
      * lb_consumer - A charm which requires loadbalancers
      * lb_provider_reactive - A reactive charm which provides loadbalancers
      * lb_consumer_reactive - A reactive charm which requires loadbalancers

    Each of these will need to be passed to `ops_test.build_charm()`.
    """
    return LBCharms(ops_test)


class LBCharms:
    def __init__(self, ops_test):
        self._ops_test = ops_test
        self._lb_lib_url = "loadbalancer-interface"
        self._lb_provider = None
        self._lb_consumer = None
        self._lb_provider_reactive = None
        self._lb_consumer_reactive = None

    def _render(self, charm_resource):
        with resource_path("loadbalancer_interface", "examples") as rp:
            assert isinstance(self._lb_lib_url, Path)
            if (rp / charm_resource / "charmcraft.yaml").exists():
                shutil.copy2(self._lb_lib_url, rp / charm_resource)
                lb_url = f"file:./{self._lb_lib_url.name}"
            else:
                lb_url = f"file://{self._lb_lib_url}#egg=loadbalancer_interface"
            return self._ops_test.render_charm(
                rp / charm_resource,
                include=["wheelhouse.txt", "requirements.txt"],
                lb_lib_url=lb_url,
            )

    @property
    def lb_provider(self):
        if self._lb_provider is None:
            self._lb_provider = self._render("lb-provider")
        return self._lb_provider

    @property
    def lb_consumer(self):
        if self._lb_consumer is None:
            self._lb_consumer = self._render("lb-consumer")
        return self._lb_consumer

    @property
    def lb_provider_reactive(self):
        if self._lb_provider_reactive is None:
            self._lb_provider_reactive = self._render("lb-provider-reactive")
        return self._lb_provider_reactive

    @property
    def lb_consumer_reactive(self):
        if self._lb_consumer_reactive is None:
            self._lb_consumer_reactive = self._render("lb-consumer-reactive")
        return self._lb_consumer_reactive
