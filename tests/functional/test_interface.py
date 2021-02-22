from collections import defaultdict

from ops.charm import CharmBase
from ops.model import Unit
from ops.testing import Harness

from loadbalancer_interface import LBProvider, LBConsumers


def test_interface():
    provider = Harness(ProviderCharm, meta=ProviderCharm._meta)
    consumer = Harness(ConsumerCharm, meta=ConsumerCharm._meta)
    provider.begin()
    consumer.begin()

    peer_units = defaultdict(list)

    # Helpers
    def add_peer_unit(harness):
        units = [harness.charm.unit] + peer_units[harness]
        next_unit_num = max(int(unit.name.split("/")[1]) for unit in units) + 1
        new_unit = Unit(
            "/".join((harness.charm.app.name, str(next_unit_num))),
            harness.charm.unit._backend,
            harness.charm.unit._cache,
        )
        peer_units[harness].append(new_unit)
        return new_unit

    def get_rel_data(harness, src):
        if hasattr(src, "name"):
            src = src.name
        return harness.get_relation_data(harness._rid, src)

    def update_rel_data(harness, data_map):
        for src, data in data_map.items():
            if hasattr(src, "name"):
                src = src.name
            harness.update_relation_data(harness._rid, src, data)

    def transmit_rel_data(src_harness, dst_harness):
        data = {}
        for src in [src_harness.charm.app, src_harness.charm.unit] + peer_units[
            src_harness
        ]:
            src_data = get_rel_data(src_harness, src)
            dst_data = get_rel_data(dst_harness, src)
            # Removed keys have to be explicitly set to an empty string for the
            # harness to remove them. (TODO: file upstream bug)
            for removed in dst_data.keys() - src_data.keys():
                src_data[removed] = ""
            data[src] = src_data
        update_rel_data(dst_harness, data)

    p_charm = provider.charm
    p_app = p_charm.app
    c_charm = consumer.charm
    c_app = c_charm.app
    c_unit0 = consumer.charm.unit
    c_unit1 = add_peer_unit(consumer)

    # Setup initial relation with only Juju-provided automatic data.
    provider._rid = provider.add_relation("lb-consumers", c_charm.meta.name)
    consumer._rid = consumer.add_relation("lb-provider", p_charm.meta.name)
    # NB: The first unit added to the relation determines the app of the
    # relation, so it's critical to add a remote unit before any local units.
    provider.add_relation_unit(provider._rid, c_unit0.name)
    provider.add_relation_unit(provider._rid, c_unit1.name)
    provider.add_relation_unit(provider._rid, p_charm.unit.name)
    consumer.add_relation_unit(consumer._rid, p_charm.unit.name)
    consumer.add_relation_unit(consumer._rid, c_unit0.name)
    consumer.add_relation_unit(consumer._rid, c_unit1.name)
    update_rel_data(
        consumer,
        {
            c_unit1: {"ingress-address": "192.168.0.3"},
            c_unit0: {"ingress-address": "192.168.0.5"},
        },
    )

    foo_id = "{}:foo".format(provider._rid)
    bar_id = "{}:bar".format(provider._rid)

    # Confirm that only leaders set the version.
    assert not get_rel_data(provider, p_app)
    provider.set_leader(True)
    p_charm.lb_consumers._set_version()
    assert get_rel_data(provider, p_app) == {"version": "1"}
    assert not c_charm.lb_provider.is_available  # waiting on remote version
    assert not c_charm.lb_provider.can_request  # waiting on remote version

    # Transmit version, but non-leader still can't make requests
    transmit_rel_data(provider, consumer)
    assert c_charm.lb_provider.is_available
    assert not c_charm.lb_provider.can_request  # not leader

    # Verify that becoming leader completes the version negotiation process and
    # allows sending requests.
    consumer.set_leader(True)
    c_charm.lb_provider._set_version()
    assert c_charm.lb_provider.can_request
    assert get_rel_data(consumer, c_app) == {"version": "1"}
    transmit_rel_data(consumer, provider)

    # Test creating and sending a request.
    c_charm.request_lb("foo")
    transmit_rel_data(consumer, provider)
    assert foo_id in p_charm.lb_consumers.state.known_requests
    assert p_charm.lb_consumers.all_requests[0].backends == [
        "192.168.0.5",
        "192.168.0.3",
    ]
    assert p_charm.changes == {"foo": 1}

    # Test receiving the response
    assert not c_charm.active_lbs
    assert not c_charm.failed_lbs
    transmit_rel_data(provider, consumer)
    assert c_charm.changes == {"foo": 1}
    assert c_charm.active_lbs == {"foo"}
    assert not c_charm.failed_lbs
    assert c_charm.lb_provider.get_response("foo").address == "lb-foo"

    # Test default updates being tracked
    update_rel_data(
        consumer,
        {
            c_unit1: {"ingress-address": "192.168.0.4"},
            c_unit0: {"ingress-address": "192.168.0.6"},
        },
    )
    transmit_rel_data(consumer, provider)
    transmit_rel_data(provider, consumer)
    assert p_charm.changes == {"foo": 3}
    # Note: Since the request didn't change, the requires side doesn't see
    # a change in the response.
    assert c_charm.changes == {"foo": 1}
    assert c_charm.active_lbs == {"foo"}
    assert not c_charm.failed_lbs

    # Test updating the request and getting an updated response.
    c_charm.request_lb("foo", ["192.168.0.5"])
    transmit_rel_data(consumer, provider)
    transmit_rel_data(provider, consumer)
    assert p_charm.lb_consumers.all_requests[0].backends == ["192.168.0.5"]
    assert p_charm.changes == {"foo": 4}
    assert c_charm.changes == {"foo": 2}
    assert c_charm.active_lbs == {"foo"}
    assert not c_charm.failed_lbs

    # Test sending a second request
    c_charm.request_lb("bar")
    transmit_rel_data(consumer, provider)
    transmit_rel_data(provider, consumer)
    assert bar_id in p_charm.lb_consumers.state.known_requests
    assert c_charm.active_lbs == {"foo"}
    assert c_charm.failed_lbs == {"bar"}

    # Test request removal
    c_charm.lb_provider.remove_request("bar")
    transmit_rel_data(consumer, provider)
    assert foo_id in p_charm.lb_consumers.state.known_requests
    assert bar_id not in p_charm.lb_consumers.state.known_requests
    assert len(p_charm.lb_consumers.all_requests) == 1

    # Test response revocation
    req = p_charm.lb_consumers.all_requests[0]
    p_charm.lb_consumers.revoke_response(req)
    transmit_rel_data(provider, consumer)
    assert not c_charm.active_lbs


# TODO: Replace these with the example charms.
class ProviderCharm(CharmBase):
    _meta = """
        name: provider
        provides:
          lb-consumers:
            interface: loadbalancer
    """

    def __init__(self, *args):
        super().__init__(*args)
        self.lb_consumers = LBConsumers(self, "lb-consumers")

        self.framework.observe(self.lb_consumers.on.requests_changed, self._update_lbs)

        self.changes = {}

    def _update_lbs(self, event):
        for request in self.lb_consumers.new_requests:
            self.changes.setdefault(request.name, 0)
            self.changes[request.name] += 1
            if request.name == "foo":
                request.response.address = "lb-" + request.name
            else:
                request.response.error = request.response.error_types.unsupported
                request.response.error_message = "No reason"
            self.lb_consumers.send_response(request)
        for request in self.lb_consumers.removed_requests:
            self.lb_consumers.revoke_response(request)


class ConsumerCharm(CharmBase):
    _meta = """
        name: consumer
        requires:
          lb-provider:
            interface: loadbalancer
    """

    def __init__(self, *args):
        super().__init__(*args)
        self._to_break = False
        self.lb_provider = LBProvider(self, "lb-provider")

        self.framework.observe(self.lb_provider.on.response_changed, self._update_lbs)

        self.changes = {}
        self.active_lbs = set()
        self.failed_lbs = set()

    def request_lb(self, name, backends=None):
        request = self.lb_provider.get_request(name)
        request.protocol = request.protocols.https
        request.port_mapping = {443: 443}
        if backends is not None:
            request.backends = backends
        self.lb_provider.send_request(request)

    def _update_lbs(self, event):
        for response in self.lb_provider.new_responses:
            self.changes.setdefault(response.name, 0)
            self.changes[response.name] += 1
            if not response.error:
                self.active_lbs.add(response.name)
                self.failed_lbs.discard(response.name)
            else:
                self.active_lbs.discard(response.name)
                self.failed_lbs.add(response.name)
            self.lb_provider.ack_response(response)
        for response in self.lb_provider.revoked_responses:
            self.active_lbs.discard(response.name)
            self.failed_lbs.discard(response.name)
