from hashlib import md5

from cached_property import cached_property

from ops.framework import StoredState
from ops.model import ModelError

from .base import LBBase, Request, Response


class LBProvider(LBBase):
    """ API used to interact with the provider of loadbalancers.
    """
    state = StoredState()

    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)
        # just call this to enforce that only one app can be related
        self.model.get_relation(relation_name)

    @property
    def relation(self):
        return self.relations[0] if self.relations else None

    def request(self, name, **kwargs):
        """ Request a load balancer / ingress endpoint from the provider.

        If a request with the given name already exists, it will be updated.
        """
        if not self.charm.unit.is_leader():
            raise ModelError('Unit is not leader')
        if not self.relation:
            raise ModelError('Relation not available')
        request = Request._read(self.relation, self.charm.app, name)
        if request:
            request._update(kwargs)
        else:
            request = Request(self.relation, self.charm.app,
                              name=name, **kwargs)
        request._write(self.relation, self.charm.app)

    def get_response(self, name):
        """ Get a specific loadbalancer response by name, or None.
        """
        return Response._read(self.relation, self.relation.app, name)

    @cached_property
    def responses(self):
        """ A list of all responses which are available.
        """
        return [response
                for relation in self.relations
                for response in Response._read_all(relation, relation.app)]

    @cached_property
    def hash(self):
        if not self.responses:
            return None
        hashes = [r.hash for r in self.responses]
        return md5(str(hashes).encode('utf8')).hexdigest()
