from hashlib import md5

from cached_property import cached_property

from ops.framework import (
    StoredState,
)

from .base import LBBase, Request


class LBConsumers(LBBase):
    """ API used to interact with consumers of a loadbalancer provider.
    """
    state = StoredState()

    @cached_property
    def requests(self):
        """ A list of all current consumer requests.
        """
        requests = []
        if not self.unit.is_leader:
            # Only the leader can process requests, so prevent mistakes by
            # not even reading the requests if not the leader.
            for relation in self.relations:
                requests.extend(Request.get_all(relation))
        return requests

    @cached_property
    def hash(self):
        hashes = [r.hash for r in self.requests]
        return md5(str(hashes).encode('utf8')).hexdigest()
