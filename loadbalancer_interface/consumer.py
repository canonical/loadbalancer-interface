from hashlib import md5

from ops.framework import (
    StoredState,
)

from .base import LBBase, Response


class LBConsumer(LBBase):
    state = StoredState()

    @property
    def responses(self):
        """ A dict of all name to response instances which are available.
        """
        responses = {}
        for relation in self.relations:
            for response in Response.get_all(relation):
                responses[response.name] = response
        return responses

    @property
    def hash(self):
        hashes = [r.hash for r in self.requests]
        return md5(str(hashes).encode('utf8')).hexdigest()
