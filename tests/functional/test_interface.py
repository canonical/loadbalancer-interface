import pytest

from ops.charm import CharmBase
from ops.model import Unit
from ops.testing import Harness

from loadbalancer_interface import LBProvider, LBConsumers


@pytest.mark.xfail
def test_interface():
    provider = Harness(ProviderCharm, meta=ProviderCharm._meta)
    consumer = Harness(ConsumerCharm, meta=ConsumerCharm._meta)
    provider.begin()
    consumer.begin()

    def get_rel_data(harness, rid, src):
        return harness.get_relation_data(rid, src)

    def update_rel_data(harness, rid, src_data_map):
        for src, data in src_data_map.items():
            harness.update_relation_data(rid, src, data)

    def next_unit(unit):
        name, num = unit.name.split('/')
        num = str(int(num) + 1)
        return Unit('/'.join((name, num)), unit._backend, unit._cache)

    p_charm = provider.charm
    p_app = p_charm.app
    c_charm = consumer.charm
    c_app = c_charm.app
    c_unit0 = consumer.charm.unit
    c_unit1 = next_unit(consumer.charm.unit)

    p_rid = provider.add_relation('clients', c_charm.meta.name)
    c_rid = consumer.add_relation('loadbalancer', p_charm.meta.name)

    assert not get_rel_data(provider, p_rid, p_app.name)
    provider.set_leader(True)
    assert get_rel_data(provider, p_rid, p_app.name) == {'version': '1'}

    provider.add_relation_unit(p_rid, c_unit0.name)
    provider.add_relation_unit(p_rid, c_unit1.name)
    update_rel_data(provider, p_rid, {
        c_unit0.name: {'ingress-address': '192.168.0.1'},
        c_unit1.name: {'ingress-address': '192.168.0.2'},
    })
    assert not p_charm.clients.relations  # still waiting on remote version

    consumer.set_leader(True)
    assert get_rel_data(consumer, c_rid, c_app.name) == {'version': '1'}

    update_rel_data(provider, p_rid, {
        c_app.name: get_rel_data(consumer, c_rid, c_app.name),
    })
    assert p_charm.clients.relations  # should now see the relation

    assert not p_charm.clients.is_changed
    # XXX not yet implemented, so assert below will fail
    c_charm.loadbalancer.request('foo',
                                 traffic_type='tcp',
                                 backend_port=80,
                                 )
    update_rel_data(provider, p_rid, {
        c_app.name: get_rel_data(consumer, c_rid, c_app.name),
    })
    assert p_charm.clients.is_changed


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
