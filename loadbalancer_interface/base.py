import weakref
from operator import attrgetter

from cached_property import cached_property

from ops.framework import (
    Object,
)

from . import schemas


class VersionedInterface(Object):
    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)
        self.charm = weakref.proxy(charm)
        self.relation_name = relation_name

        # Future-proof against the need to evolve the relation protocol
        # by ensuring that we agree on a version number before starting.
        # This may or may not be made moot by a future feature in Juju.
        self._set_version()

    def _set_version(self):
        if self.unit.is_leader():
            for relation in self.model.relations.get(self.relation_name, []):
                relation.data[self.app]["version"] = str(schemas.max_version)

    @cached_property
    def relations(self):
        relations = self.model.relations.get(self.relation_name, [])
        return [
            relation
            for relation in sorted(relations, key=attrgetter("id"))
            if self._schema(relation)
        ]

    def _schema(self, relation=None):
        if relation is None:
            return schemas.versions[schemas.max_version]
        if relation.app not in relation.data:
            return None
        data = relation.data[relation.app]
        if "version" not in data:
            return None
        remote_version = int(data["version"])
        return schemas.versions[min((schemas.max_version, remote_version))]

    @property
    def model(self):
        return self.framework.model

    @property
    def app(self):
        return self.charm.app

    @property
    def unit(self):
        return self.charm.unit
