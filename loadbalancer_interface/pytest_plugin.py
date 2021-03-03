import weakref
from contextlib import contextmanager
from pathlib import Path

import pytest

from pytest_operator import OperatorTest


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


def pytest_configure(config):
    config.addinivalue_line("markers", "lb_charms")


@pytest.fixture(autouse=True, scope="class")
def lb_charms(request):
    """Fixture which injects the lb_charms attribute to marked OperatorTests.

    Any subclass of OperatorTest which is marked with @pytest.mark.lb_charms
    will have a lb_charms attribute injected into it which has the following
    attributes:

      * lb_provider - A charm which provides loadbalancers
      * lb_consumer - A charm which requires loadbalancers
      * lb_provider_reactive - A reactive charm which provides loadbalancers
      * lb_consumer_reactive - A reactive charm which requires loadbalancers
    """
    marker = request.node.get_closest_marker("lb_charms")
    if not marker:
        return
    if not issubclass(getattr(request, "cls", None), OperatorTest):
        return
    request.cls.lb_lib_url = "loadbalancer-interface"
    request.cls.lb_charms = property(lambda test_case: LBCharms(test_case))


class LBCharms:
    def __init__(self, test_case):
        self._test_case = weakref.proxy(test_case)
        self._lb_provider = None
        self._lb_consumer = None
        self._lb_provider_reactive = None
        self._lb_consumer_reactive = None

    def _render(self, charm_resource):
        with resource_path("loadbalancer_interface", "examples") as rp:
            return self._test_case.render_charm(
                rp / charm_resource,
                include=["wheelhouse.txt", "requirements.txt"],
                lb_lib_url=self._test_case.lb_lib_url,
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
