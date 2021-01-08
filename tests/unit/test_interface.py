from ops.charm import CharmBase
from ops.testing import Harness

from loadbalancer_interface import LBProvider, LBConsumers


def test_interface():
    provider = Harness(ProviderCharm, meta=ProviderCharm.meta)
    consumer = Harness(ConsumerCharm, meta=ConsumerCharm.meta)
    provider.begin()
    consumer.begin()

    pcharm = provider.charm
    papp = pcharm.app
    punit = provider.charm.unit
    prid = None
    ccharm = consumer.charm
    capp = ccharm.app
    cunit = ccharm.unit
    crid = None

    def prd(src):
        return provider.get_relation_data(prid, src.name)

    def crd(src):
        return consumer.get_relation_data(crid, src.name)

    assert not punit.is_leader()
    prid = provider.add_relation('clients', capp.name)
    assert not prd(papp)
    provider.set_leader(True)
    assert prd(papp) == {'version': '1'}

    provider.add_relation_unit(prid, cunit.name)
    provider.update_relation_data(prid, cunit.name, {
        'ingress-address': '192.168.0.1',
    })
    assert not pcharm.clients.relations  # still waiting on remote version

    consumer.set_leader(True)
    crid = consumer.add_relation('loadbalancer', capp.name)
    assert crd(capp) == {'version': '1'}

    provider.update_relation_data(prid, capp.name, crd(capp))
    assert pcharm.clients.relations  # should now see the relation

    assert not pcharm.clients.is_changed
    # XXX not yet implemented, so assert below will fail
    ccharm.loadbalancer.request('foo',
                                traffic_type='tcp',
                                backend_port=80)
    provider.update_relation_data(prid, capp.name, crd(capp))
    assert pcharm.clients.is_changed


class ProviderCharm(CharmBase):
    meta = """
        name: provider
        provides:
          clients:
            interface: loadbalancer
    """

    def __init__(self, *args):
        super().__init__(*args)
        self.clients = LBConsumers(self, 'clients')


class ConsumerCharm(CharmBase):
    meta = """
        name: consumer
        requires:
          loadbalancer:
            interface: loadbalancer
    """

    def __init__(self, *args):
        super().__init__(*args)
        self.loadbalancer = LBProvider(self, 'loadbalancer')
