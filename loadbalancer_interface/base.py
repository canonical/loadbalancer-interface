import weakref
from operator import attrgetter
from typing import Iterable, Sequence, Union

from cached_property import cached_property

from ops.framework import (
    Object,
)


VERSION = '1'


class Response:
    @classmethod
    def get_all(cls, relation):
        raise NotImplementedError()

    def __init__(self, relation):
        self.relation = relation

    @property
    def hash(self):
        raise NotImplementedError()


class HealthCheck:
    def __init__(self,
                 traffic_type: str,
                 port: int,
                 path: str = None,
                 interval: int = 30,
                 retries: int = 3):
        self.traffic_type = traffic_type
        self.port = port
        self.path = path
        self.interval = interval
        self.retries = retries


class Request:
    @classmethod
    def get_all(cls, app, relation):
        raise NotImplementedError()

    def __init__(self,
                 app,
                 relation,
                 *,
                 traffic_type: str,
                 backends: Iterable[str] = None,
                 backend_port: Union[int, Iterable[int]],
                 algorithm: Sequence[str] = None,
                 sticky: bool = False,
                 health_checks: Iterable[HealthCheck] = None,
                 public: bool = True,
                 tls_termination: bool = False,
                 tls_cert: str = None,
                 tls_key: str = None,
                 ingress_address: str = None,
                 ingress_port: Union[int, Iterable[int]] = None,
                 response: Response = None,
                 ):
        self.app = app
        self.relation = relation
        self.traffic_type = traffic_type
        self.backends = backends
        self.backend_port = backend_port
        self.algorithm = algorithm
        self.sticky = sticky
        self.health_checks = health_checks
        self.public = public
        self.tls_termination = tls_termination
        self.tls_cert = tls_cert
        self.tls_key = tls_key
        self.ingress_address = ingress_address
        self.ingress_port = ingress_port
        self.response = response

    @property
    def hash(self):
        raise NotImplementedError()

    def write(self):
        raise NotImplementedError()


class LBBase(Object):
    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)
        self.charm = weakref.proxy(charm)
        self.relation_name = relation_name
        self.state.set_default(hash=None)

        # Future-proof against the need to evolve the relation protocol
        # by ensuring that we agree on a version number before starting.
        # This may or may not be made moot by a future feature in Juju.
        for event in (charm.on[relation_name].relation_created,
                      charm.on.leader_elected,
                      charm.on.upgrade_charm):
            self.framework.observe(event, self._set_version)

    def _set_version(self, event):
        if self.unit.is_leader():
            if hasattr(event, 'relation'):
                relations = [event.relation]
            else:
                relations = self.model.relations.get(self.relation_name, [])
            for relation in relations:
                relation.data[self.app]['version'] = str(VERSION)

    @cached_property
    def relations(self):
        relations = self.model.relations.get(self.relation_name, [])
        return [relation
                for relation in sorted(relations, key=attrgetter('id'))
                if VERSION == relation.data.get(relation.app,
                                                {}).get('version')]

    @property
    def is_changed(self):
        return self.state.hash == self.hash

    @is_changed.setter
    def is_changed(self, value):
        if not value:
            self.state.hash = self.hash

    @property
    def model(self):
        return self.framework.model

    @property
    def app(self):
        return self.charm.app

    @property
    def unit(self):
        return self.charm.unit
