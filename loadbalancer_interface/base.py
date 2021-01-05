import weakref
from operator import attrgetter

from ops.framework import (
    Object,
)


VERSION = '1'


class Request:
    @classmethod
    def get_all(cls, app, relation):
        raise NotImplementedError()

    def __init__(self, app, relation):
        self.app = app
        self.relation = relation
        self.response = None

    @property
    def hash(self):
        raise NotImplementedError()


class Response:
    @classmethod
    def get_all(cls, relation):
        raise NotImplementedError()

    def __init__(self, relation):
        self.relation = relation

    @property
    def hash(self):
        raise NotImplementedError()


class LBBase(Object):
    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)
        self.charm = weakref.proxy(charm)
        self.relation_name = relation_name
        self.state.set_default(hash=None)

        # Future-proof against the need to evolve the relation protocol
        # by ensuring that we agree on a version number before starting.
        # This may be made moot by a future feature in Juju.
        self.relations = []
        for relation in sorted(self.model.relations[self.relation_name],
                               key=attrgetter('id')):
            relation.data[self.app]['version'] = VERSION
            if relation.data.get(relation.app, {}).get('version') == VERSION:
                self.relations.append(relation)

    @property
    def hash(self):
        raise NotImplementedError()

    @property
    def is_changed(self):
        return self.state.hash == self.hash

    @is_changed.setter
    def is_changed(self, value):
        if not value:
            self.state.hash = self.hash

    @property
    def model(self):
        return self.framework.model

    @property
    def app(self):
        return self.charm.app

    @property
    def unit(self):
        return self.charm.app
