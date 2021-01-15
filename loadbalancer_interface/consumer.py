from hashlib import md5

from cached_property import cached_property

from ops.framework import (
    StoredState,
)

from .base import LBBase, Request, Response


class LBConsumers(LBBase):
    """ API used to interact with consumers of a loadbalancer provider.
    """
    state = StoredState()

    @cached_property
    def all_requests(self):
        """ A list of all current consumer requests.
        """
        if not self.unit.is_leader():
            # Only the leader can process requests, so avoid mistakes
            # by not even reading the requests if not the leader.
            return []
        return [request
                for relation in self.relations
                for request in Request._read_all(relation, relation.app)]

    @property
    def new_requests(self):
        """A list of requests with changes or no response.
        """
        return [req for req in self.all_requests
                if not req.response or req.response.request_hash != req.hash]

    def respond(self, request, **kwargs):
        """ Respond to a specific request.

        Any existing response will be updated.
        """
        if request.response:
            request.response._update(**kwargs)
        else:
            request.response = Response(name=request.name,
                                        request_hash=request.hash,
                                        **kwargs)
        request.response._write(request.relation, self.charm.app)

    @cached_property
    def hash(self):
        if not self.all_requests:
            return None
        hashes = [r.hash for r in self.all_requests]
        return md5(str(hashes).encode('utf8')).hexdigest()
