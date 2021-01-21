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
        next_unit_num = max(int(unit.name.split('/')[1]) for unit in units) + 1
        new_unit = Unit('/'.join((harness.charm.app.name, str(next_unit_num))),
                        harness.charm.unit._backend,
                        harness.charm.unit._cache)
        peer_units[harness].append(new_unit)
        return new_unit

    def get_rel_data(harness, src):
        if hasattr(src, 'name'):
            src = src.name
        return harness.get_relation_data(harness._rid, src)

    def update_rel_data(harness, data_map):
        for src, data in data_map.items():
            if hasattr(src, 'name'):
                src = src.name
            harness.update_relation_data(harness._rid, src, data)

    def transmit_rel_data(src_harness, dest_harness):
        data = {
            src_harness.charm.app: get_rel_data(src_harness,
                                                src_harness.charm.app),
            src_harness.charm.unit: get_rel_data(src_harness,
                                                 src_harness.charm.unit),
        }
        data.update({unit: get_rel_data(src_harness, unit)
                     for unit in peer_units[src_harness]})
        update_rel_data(dest_harness, data)

    p_charm = provider.charm
    p_app = p_charm.app
    c_charm = consumer.charm
    c_app = c_charm.app
    c_unit0 = consumer.charm.unit
    c_unit1 = add_peer_unit(consumer)

    # Setup initial relation with only Juju-provided automatic data.
    provider._rid = provider.add_relation('lb-consumers', c_charm.meta.name)
    consumer._rid = consumer.add_relation('lb-provider', p_charm.meta.name)
    # NB: The first unit added to the relation determines the app of the
    # relation, so it's critical to add a remote unit before any local units.
    provider.add_relation_unit(provider._rid, c_unit0.name)
    provider.add_relation_unit(provider._rid, c_unit1.name)
    provider.add_relation_unit(provider._rid, p_charm.unit.name)
    consumer.add_relation_unit(consumer._rid, p_charm.unit.name)
    consumer.add_relation_unit(consumer._rid, c_unit0.name)
    consumer.add_relation_unit(consumer._rid, c_unit1.name)
    update_rel_data(consumer, {
        c_unit1: {'ingress-address': '192.168.0.3'},
        c_unit0: {'ingress-address': '192.168.0.5'},
    })

    foo_id = '{}:foo'.format(provider._rid)
    bar_id = '{}:bar'.format(provider._rid)

    # Confirm that only leaders set the version.
    assert not get_rel_data(provider, p_app)
    provider.set_leader(True)
    assert get_rel_data(provider, p_app) == {'version': '1'}
    assert not c_charm.lb_provider.is_available  # waiting on remote version
    assert not c_charm.lb_provider.can_request  # waiting on remote version

    # Transmit version, but non-leader still can't make requests
    transmit_rel_data(provider, consumer)
    assert c_charm.lb_provider.is_available
    assert not c_charm.lb_provider.can_request  # not leader

    # Verify that becoming leader completes the version negotiation process and
    # allows sending requests.
    consumer.set_leader(True)
    assert c_charm.lb_provider.can_request
    assert get_rel_data(consumer, c_app) == {'version': '1'}
    transmit_rel_data(consumer, provider)

    # Test creating and sending a request.
    c_charm.request_lb('foo')
    transmit_rel_data(consumer, provider)
    assert foo_id in p_charm.managed_lbs
    assert p_charm.managed_lbs[foo_id].backends == ['192.168.0.5',
                                                    '192.168.0.3']

    # Test receiving the response
    assert not c_charm.active_lbs
    assert not c_charm.failed_lbs
    transmit_rel_data(provider, consumer)
    assert c_charm.active_lbs == {'lb-foo': 1}
    assert not c_charm.failed_lbs

    # Test updating the request and getting an updated response.
    c_charm.request_lb('foo', ['192.168.0.5'])
    transmit_rel_data(consumer, provider)
    assert p_charm.managed_lbs[foo_id].backends == ['192.168.0.5']
    transmit_rel_data(provider, consumer)
    assert c_charm.active_lbs == {'lb-foo': 2}
    assert not c_charm.failed_lbs

    # Test sending a second request
    c_charm.request_lb('bar')
    transmit_rel_data(consumer, provider)
    transmit_rel_data(provider, consumer)
    assert bar_id in p_charm.managed_lbs
    assert c_charm.active_lbs == {'lb-foo': 2}
    assert c_charm.failed_lbs == {'bar'}


class ProviderCharm(CharmBase):
    _meta = """
        name: provider
        provides:
          lb-consumers:
            interface: loadbalancer
    """

    def __init__(self, *args):
        super().__init__(*args)
        self.lb_consumers = LBConsumers(self, 'lb-consumers')

        self.framework.observe(self.lb_consumers.on.requests_changed,
                               self._create_lbs)

        self.managed_lbs = {}

    def _create_lbs(self, event):
        for request in self.lb_consumers.new_requests:
            if request.name == 'foo':
                request.response.success = True
                request.response.address = 'lb-' + request.name
            else:
                request.response.success = False
                request.response.message = 'No reason'
            self.managed_lbs[request.id] = request
            self.lb_consumers.send_response(request)


class ConsumerCharm(CharmBase):
    _meta = """
        name: consumer
        requires:
          lb-provider:
            interface: loadbalancer
    """

    def __init__(self, *args):
        super().__init__(*args)
        self.lb_provider = LBProvider(self, 'lb-provider')

        self.framework.observe(self.lb_provider.on.responses_changed,
                               self._get_lb)

        self.saw_available = False
        self.active_lbs = dict()
        self.failed_lbs = set()

    def request_lb(self, name, backends=None):
        request = self.lb_provider.get_request(name)
        request.traffic_type = 'https'
        request.backend_ports = [443]
        if backends is not None:
            request.backends = backends
        self.lb_provider.send_request(request)

    def _get_lb(self, event):
        for response in self.lb_provider.new_responses:
            if response.success:
                self.active_lbs.setdefault(response.address, 0)
                self.active_lbs[response.address] += 1
            else:
                self.failed_lbs.add(response.name)
            self.lb_provider.ack_response(response)
