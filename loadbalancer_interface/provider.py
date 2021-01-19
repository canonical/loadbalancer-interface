from cached_property import cached_property

from ops.framework import (
    StoredState,
    EventBase,
    EventSource,
    ObjectEvents,
)
from ops.model import ModelError

from .base import LBBase


class LBProviderAvailable(EventBase):
    pass


class LBResponsesChanged(EventBase):
    pass


class LBProviderEvents(ObjectEvents):
    available = EventSource(LBProviderAvailable)
    responses_changed = EventSource(LBResponsesChanged)


class LBProvider(LBBase):
    """ API used to interact with the provider of loadbalancers.
    """
    state = StoredState()
    on = LBProviderEvents()

    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)
        self.relation_name = relation_name
        # just call this to enforce that only one app can be related
        self.model.get_relation(relation_name)
        self.state.set_default(response_hashes={},
                               was_available=False)

        for event in (charm.on[relation_name].relation_created,
                      charm.on[relation_name].relation_joined,
                      charm.on[relation_name].relation_changed,
                      charm.on[relation_name].relation_departed,
                      charm.on[relation_name].relation_broken):
            self.framework.observe(event, self._check_provider)

    def _check_provider(self, event):
        if self.is_available:
            if not self.state.was_available:
                self.state.was_available = True
                self.on.available.emit()
            if self.is_changed:
                self.on.responses_changed.emit()
        else:
            self.state.was_available = False

    @property
    def relation(self):
        return self.relations[0] if self.relations else None

    def get_request(self, name):
        """ Get or create a Load Balancer Request object.
        """
        if not self.charm.unit.is_leader():
            raise ModelError('Unit is not leader')
        if not self.relation:
            raise ModelError('Relation not available')
        schema = self._schema(self.relation)
        local_data = self.relation.data[self.app]
        remote_data = self.relation.data[self.relation.app]
        request_key = 'request_' + name
        response_key = 'response_' + name
        if request_key in local_data:
            request_sdata = local_data[request_key]
            response_sdata = remote_data.get(response_key)
            request = schema.Request.loads(request_sdata, response_sdata)
        else:
            request = schema.Request(name)
        return request

    def get_response(self, name):
        """ Get a specific Load Balancer Response by name.

        This is equivalent to `get_request(name).response`.
        """
        return self.get_request(name).response

    def send_request(self, request):
        """ Send a specific request.
        """
        key = 'request_' + request.name
        self.relation.data[self.app][key] = request.dumps()
        self.state.response_hashes[request.name] = None

    @cached_property
    def all_responses(self):
        """ A list of all responses which are available.
        """
        local_data = self.relation.data[self.app]
        request_names = [key[len('request_'):]
                         for key in local_data.keys()
                         if key.startswith('request_')]
        return [self.get_request(name).response
                for name in request_names]

    @property
    def new_responses(self):
        """ A list of all responses which have not yet been acknowledged as
        handled or which have changed.
        """
        return [response
                for response in self.all_responses
                if self.state.response_hashes[response.name] != response.hash]

    def ack_response(self, response):
        """ Acknowledge that a given response has been handled.
        """
        self.state.response_hashes[response.name] = response.hash

    @property
    def is_changed(self):
        return bool(self.new_responses)

    @property
    def is_available(self):
        return bool(self.relation)

    def manage_flags(self):
        """ Used to interact with charms.reactive-base charms.
        """
        from charms.reactive import toggle_flag
        prefix = 'endpoint.' + self.relation_name
        toggle_flag(prefix + '.available', self.is_available)
        toggle_flag(prefix + '.responses_changed', self.is_changed)
