from operator import attrgetter

from cached_property import cached_property

from ops.framework import (
    StoredState,
    EventBase,
    EventSource,
    ObjectEvents,
)

from .base import VersionedInterface


class LBRequestsChanged(EventBase):
    pass


class LBConsumersEvents(ObjectEvents):
    requests_changed = EventSource(LBRequestsChanged)


class LBConsumers(VersionedInterface):
    """API used to interact with consumers of a loadbalancer provider."""

    state = StoredState()
    on = LBConsumersEvents()

    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)
        self.relation_name = relation_name
        self.state.set_default(known_requests={})

        for event in (
            charm.on[relation_name].relation_created,
            charm.on[relation_name].relation_joined,
            charm.on[relation_name].relation_changed,
        ):
            self.framework.observe(event, self._check_consumers)

    def _check_consumers(self, event):
        if self.is_changed:
            self.on.requests_changed.emit()

    @cached_property
    def all_requests(self):
        """A list of all current consumer requests."""
        if not self.unit.is_leader():
            # Only the leader can process requests, so avoid mistakes
            # by not even reading the requests if not the leader.
            return []
        requests = []
        for relation in self.relations:
            schema = self._schema(relation)
            local_data = relation.data[self.app]
            remote_data = relation.data[relation.app]
            for key, request_sdata in sorted(remote_data.items()):
                if not key.startswith("request_"):
                    continue
                name = key[len("request_") :]
                response_sdata = local_data.get("response_" + name)
                request = schema.Request.loads(name, request_sdata, response_sdata)
                request.relation = relation
                if not request.backends:
                    for unit in sorted(relation.units, key=attrgetter("name")):
                        addr = relation.data[unit].get("ingress-address")
                        if addr:
                            request.backends.append(addr)
                requests.append(request)
                self.state.known_requests.setdefault(request.id, None)
        return requests

    @property
    def new_requests(self):
        """A list of requests with changes or no response."""
        return [
            request
            for request in self.all_requests
            if request.hash != self.state.known_requests[request.id]
        ]

    @property
    def removed_requests(self):
        """A list of requests which have been removed, either explicitly or
        because the relation was removed.
        """
        current_ids = {request.id for request in self.all_requests}
        unknown_ids = self.state.known_requests.keys() - current_ids
        schema = self._schema()
        return [
            schema.Request._from_id(req_id, self.relations)
            for req_id in sorted(unknown_ids)
        ]

    def send_response(self, request):
        """Send a specific request's response."""
        request.response.received_hash = request.sent_hash
        key = "response_" + request.name
        request.relation.data[self.app][key] = request.response.dumps()
        self.state.known_requests[request.id] = request.hash
        if not self.new_requests:
            try:
                from charms.reactive import clear_flag

                prefix = "endpoint." + self.relation_name
                clear_flag(prefix + ".requests_changed")
            except ImportError:
                pass  # not being used in a reactive charm

    def revoke_response(self, request):
        """Revoke / remove the response for a given request."""
        if request.id:
            self.state.known_requests.pop(request.id, None)
        if request.relation:
            key = "response_" + request.name
            request.relation.data.get(self.app, {}).pop(key, None)

    @property
    def is_changed(self):
        return bool(self.new_requests or self.removed_requests)

    def manage_flags(self):
        """Used to interact with charms.reactive-base charms."""
        from charms.reactive import toggle_flag

        prefix = "endpoint." + self.relation_name
        toggle_flag(prefix + ".requests_changed", self.is_changed)
