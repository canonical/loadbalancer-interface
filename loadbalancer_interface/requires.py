from cached_property import cached_property

from ops.framework import (
    StoredState,
    EventBase,
    EventSource,
    ObjectEvents,
)
from ops.model import ModelError

from .base import VersionedInterface


class LBProviderAvailable(EventBase):
    pass


class LBResponseAvailable(EventBase):
    pass


class LBResponseChanged(EventBase):
    pass


class LBProviderEvents(ObjectEvents):
    available = EventSource(LBProviderAvailable)
    response_available = EventSource(LBResponseAvailable)
    response_changed = EventSource(LBResponseChanged)


class LBProvider(VersionedInterface):
    """API used to interact with the provider of loadbalancers."""

    state = StoredState()
    on = LBProviderEvents()

    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)
        self.relation_name = relation_name
        # just call this to enforce that only one app can be related
        self.model.get_relation(relation_name)
        self.state.set_default(
            response_hashes={}, was_available=False, was_response_available=False
        )

        for event in (
            charm.on[relation_name].relation_created,
            charm.on[relation_name].relation_joined,
            charm.on[relation_name].relation_changed,
            charm.on[relation_name].relation_departed,
            charm.on[relation_name].relation_broken,
        ):
            self.framework.observe(event, self._check_provider)

    def _check_provider(self, event):
        if self.is_available:
            if not self.state.was_available:
                self.state.was_available = True
                self.on.available.emit()
            if not self.state.was_response_available:
                self.state.was_response_available = True
                self.on.response_available.emit()
            if self.is_changed:
                self.on.response_changed.emit()
        elif self.state.was_available:
            self.state.was_available = False
            self.state.was_response_available = False
            if self.state.response_hashes:
                self.state.response_hashes = {}
                self.on.response_changed.emit()

    @property
    def relation(self):
        return self.relations[0] if self.relations else None

    def get_request(self, name):
        """Get or create a Load Balancer Request object.

        May raise a ModelError if unable to create a request.
        """
        if not self.charm.unit.is_leader():
            raise ModelError("Unit is not leader")
        if not self.relation:
            raise ModelError("Relation not available")
        schema = self._schema(self.relation)
        local_data = self.relation.data[self.app]
        remote_data = self.relation.data[self.relation.app]
        request_key = "request_" + name
        response_key = "response_" + name
        if request_key in local_data:
            request_sdata = local_data[request_key]
            response_sdata = remote_data.get(response_key)
            request = schema.Request.loads(name, request_sdata, response_sdata)
        else:
            request = schema.Request(name)
        return request

    def get_response(self, name):
        """Get a specific Load Balancer Response by name.

        This is equivalent to `get_request(name).response`, except that it
        will return `None` if the response is not available.
        """
        if not self.is_available:
            return None
        request = self.get_request(name)
        if not request.response:
            return None
        return request.response

    def send_request(self, request):
        """Send a specific request.

        May raise a ModelError if unable to send the request.
        """
        if not self.charm.unit.is_leader():
            raise ModelError("Unit is not leader")
        if not self.relation:
            raise ModelError("Relation not available")
        # The sent_hash is used to tell when the provider's response has been
        # updated to match our request. We can't used the request hash computed
        # on the providing side because it may not match due to default values
        # being filled in on that side (e.g., the backend addresses).
        request.sent_hash = request.hash
        key = "request_" + request.name
        self.relation.data[self.app][key] = request.dumps()

    def remove_request(self, name):
        """Remove a specific request.

        May raise a ModelError if unable to remove the request.
        """
        if not self.charm.unit.is_leader():
            raise ModelError("Unit is not leader")
        if not self.relation:
            return
        key = "request_" + name
        self.relation.data[self.app].pop(key, None)
        self.state.response_hashes.pop(name, None)

    @property
    def all_requests(self):
        """A list of all requests which have been made."""
        requests = []
        if self.relation:
            for key in sorted(self.relation.data[self.app].keys()):
                if not key.startswith("request_"):
                    continue
                requests.append(self.get_request(key[len("request_") :]))
        return requests

    @property
    def revoked_responses(self):
        """A list of responses which are no longer available."""
        return [
            request.response
            for request in self.all_requests
            if not request.response and request.name in self.state.response_hashes
        ]

    @cached_property
    def all_responses(self):
        """A list of all responses which are available."""
        return [request.response for request in self.all_requests if request.response]

    @cached_property
    def complete_responses(self):
        """A list of all responses which are up to date with their associated
        request.
        """
        return [
            request.response
            for request in self.all_requests
            if request.response.received_hash == request.sent_hash
        ]

    @property
    def new_responses(self):
        """A list of complete responses which have not yet been acknowledged as
        handled or which have changed.
        """
        acked_responses = self.state.response_hashes
        return [
            response
            for response in self.complete_responses
            if response.hash != acked_responses.get(response.name)
        ]

    def ack_response(self, response):
        """Acknowledge that a given response has been handled.

        Can be called on a revoked response as well to remove it
        from the revoked_responses list.
        """
        if response:
            self.state.response_hashes[response.name] = response.hash
        else:
            self.state.response_hashes.pop(response.name, None)
        if not self.is_changed:
            try:
                from charms.reactive import clear_flag

                prefix = "endpoint." + self.relation_name
                clear_flag(prefix + ".response.changed")
            except ImportError:
                pass  # not being used in a reactive charm

    @property
    def is_changed(self):
        return self.new_responses or self.revoked_responses

    @property
    def is_available(self):
        return bool(self.relation)

    @property
    def has_response(self):
        return bool(self.complete_responses)

    @property
    def can_request(self):
        return self.is_available and self.unit.is_leader()

    def manage_flags(self):
        """Used to interact with charms.reactive-base charms."""
        from charms.reactive import toggle_flag

        prefix = "endpoint." + self.relation_name
        toggle_flag(prefix + ".available", self.is_available)
        toggle_flag(prefix + ".response.available", self.has_response)
        toggle_flag(prefix + ".response.changed", self.is_changed)
