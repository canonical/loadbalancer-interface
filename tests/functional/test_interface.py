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

    provider._rid = provider.add_relation('clients', c_charm.meta.name)
    consumer._rid = consumer.add_relation('loadbalancer', p_charm.meta.name)
    provider.add_relation_unit(provider._rid, c_unit0.name)
    provider.add_relation_unit(provider._rid, c_unit1.name)
    provider.add_relation_unit(provider._rid, p_charm.unit.name)
    consumer.add_relation_unit(consumer._rid, c_unit0.name)
    consumer.add_relation_unit(consumer._rid, c_unit1.name)
    consumer.add_relation_unit(consumer._rid, p_charm.unit.name)
    update_rel_data(consumer, {
        c_unit1: {'ingress-address': '192.168.0.3'},
        c_unit0: {'ingress-address': '192.168.0.5'},
    })

    assert not get_rel_data(provider, p_app)
    provider.set_leader(True)
    assert get_rel_data(provider, p_app) == {'version': '1'}

    transmit_rel_data(provider, consumer)

    assert not p_charm.clients.relations  # still waiting on remote version

    consumer.set_leader(True)
    assert get_rel_data(consumer, c_app) == {'version': '1'}

    transmit_rel_data(consumer, provider)
    assert p_charm.clients.relations  # should now see the relation

    assert not p_charm.clients.is_changed
    c_charm.loadbalancer.request(name='foo',
                                 traffic_type='tcp',
                                 backend_ports=[80])
    transmit_rel_data(consumer, provider)
    assert p_charm.clients.is_changed

    assert len(p_charm.clients.new_requests) == 1
    req = p_charm.clients.new_requests[0]
    assert req.backends == ['192.168.0.5', '192.168.0.3']
    p_charm.clients.respond(req, success=True, address='my-lb')
    # TODO: Responses aren't loaded properly on the providing side, because the
    #       current implementation assumes they'll be on the same app as the
    #       request, where as on the provider side, they will be on the local
    #       app.
    # assert not p_charm.clients.new_requests

    # TODO: transmit the response back and verify it


class ProviderCharm(CharmBase):
    _meta = """
        name: provider
        provides:
          clients:
            interface: loadbalancer
    """

    def __init__(self, *args):
        super().__init__(*args)
        self.clients = LBConsumers(self, 'clients')


class ConsumerCharm(CharmBase):
    _meta = """
        name: consumer
        requires:
          loadbalancer:
            interface: loadbalancer
    """

    def __init__(self, *args):
        super().__init__(*args)
        self.loadbalancer = LBProvider(self, 'loadbalancer')
