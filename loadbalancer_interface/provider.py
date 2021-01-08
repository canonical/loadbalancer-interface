import typing
from hashlib import md5

from cached_property import cached_property

from ops.framework import (
    StoredState,
)

from .base import LBBase, Response


class LBProvider(LBBase):
    """ API used to interact with the provider of loadbalancers.
    """
    state = StoredState()

    def request(self,
                name,
                *,
                traffic_type: str,
                backends: typing.Iterable[str] = None,
                backend_port: typing.Union[int, typing.Iterable[int]],
                algorithm: typing.List[str] = None,
                sticky: bool = False,
                ):
        """ Request a load balancer / ingress endpoint from the provider.
        """
        pass

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
