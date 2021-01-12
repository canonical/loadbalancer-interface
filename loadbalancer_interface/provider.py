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

    def request(self, name, **kwargs):
        """ Request a load balancer / ingress endpoint from the provider.
        """
        if not self.charm.unit.is_leader():
            raise ModelError('Unit is not leader')
        if not self.relations:
            raise ModelError('Relation not available')
        request = Request(self.charm.app, self.relations[0], name, **kwargs)
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
