from hashlib import md5
from typing import Iterable, Sequence, Union

from cached_property import cached_property

from ops.framework import StoredState
from ops.model import ModelError

from .base import LBBase, Request, HealthCheck, Response


class LBProvider(LBBase):
    """ API used to interact with the provider of loadbalancers.
    """
    state = StoredState()

    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)
        # just call this to enforce that only one app can be related
        self.model.get_relation(relation_name)

    def request(self,
                name,
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
                ):
        """ Request a load balancer / ingress endpoint from the provider.
        """
        if not self.charm.unit.is_leader():
            raise ModelError('Unit is not leader')
        if not self.relations:
            raise ModelError('Relation not available')
        request = Request(self.charm.app,
                          self.relations[0],
                          name,
                          traffic_type=traffic_type,
                          backends=backends,
                          backend_port=backend_port,
                          algorithm=algorithm,
                          sticky=sticky,
                          health_checks=health_checks,
                          public=public,
                          tls_termination=tls_termination,
                          tls_cert=tls_cert,
                          tls_key=tls_key,
                          ingress_address=ingress_address,
                          ingress_port=ingress_port,
                          )
        request.write()

    @cached_property
    def responses(self):
        """ A dict of all name to response instances which are available.
        """
        responses = {}
        for relation in self.relations:
            for response in Response.get_all(relation):
                responses[response.name] = response
        return responses

    @cached_property
    def hash(self):
        hashes = [r.hash for r in self.responses]
        return md5(str(hashes).encode('utf8')).hexdigest()
