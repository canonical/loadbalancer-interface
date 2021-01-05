from hashlib import md5

from ops.framework import (
    StoredState,
)

from .base import LBBase, Request


class LBProducer(LBBase):
    state = StoredState()

    @property
    def requests(self):
        """ A list of all current requests.
        """
        requests = []
        for relation in self.relations:
            version = self._version_mgr.get(relation)
            if version is None:
                continue
            for request in Request.get_all(self.app, relation):
                requests.append(request)
        return requests

    @property
    def hash(self):
        hashes = [r.hash for r in self.requests]
        return md5(str(hashes).encode('utf8')).hexdigest()
