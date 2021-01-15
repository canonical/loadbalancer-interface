import json
import weakref
from hashlib import md5
from operator import attrgetter

from cached_property import cached_property
from marshmallow import Schema, fields, validates_schema, ValidationError

from ops.framework import (
    Object,
)


VERSION = '1'


class Response:
    class _Schema(Schema):
        name = fields.Str(required=True)
        success = fields.Bool(required=True)
        message = fields.Str(missing=None)
        address = fields.Str(required=True)
        request_hash = fields.Str(required=True)

        @validates_schema
        def _validate(self, data, **kwargs):
            if not data['success'] and not data['message']:
                raise ValidationError('message required on failure')

    @classmethod
    def _key(cls, name):
        return 'response_' + name

    def __init__(self, **kwargs):
        self._schema = self._Schema()
        for field, value in self._schema.load(kwargs).items():
            setattr(self, field, value)

    @classmethod
    def _read(cls, relation, app, name):
        if cls._key(name) not in relation.data[app]:
            return None
        return cls(**json.loads(relation.data[app][cls._key(name)]))

    @classmethod
    def _read_all(cls, relation, app):
        prefix = cls._key('')
        for key, value in relation.data[app].items():
            if not key.startswith(cls._key('')):
                continue
            name = key[len(prefix):]
            yield cls._read(relation, app, name)

    def _write(self, relation, app):
        relation.data[app][self._key(self.name)] = self._dumps()

    def _dumps(self):
        serialized = self._schema.dump(self)
        errors = self._schema.validate(serialized)
        if errors:
            raise ValidationError(errors)
        return json.dumps(serialized, sort_keys=True)

    @property
    def hash(self):
        return md5(self._dumps().encode('utf8')).hexdigest()


class HealthCheck:
    class _Schema(Schema):
        traffic_type = fields.Str(required=True)
        port = fields.Int(required=True)
        path = fields.Str(missing=None)
        interval = fields.Int(missing=30)
        retries = fields.Int(missing=3)

    def __init__(self, **kwargs):
        self._schema = self._Schema()
        for field, value in self._schema.load(kwargs).items():
            setattr(self, field, value)


class HealthCheckField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        return value._schema.dump(value)

    def _deserialize(self, value, attr, data, **kwargs):
        if isinstance(value, HealthCheck):
            return value
        return HealthCheck(**value)


class Request:
    class _Schema(Schema):
        name = fields.Str(required=True)
        traffic_type = fields.Str(required=True)
        backends = fields.List(fields.Str(), missing=list)
        backend_ports = fields.List(fields.Int(), required=True)
        algorithm = fields.List(fields.Str(), missing=list)
        sticky = fields.Bool(missing=False)
        health_checks = fields.List(HealthCheckField, missing=list)
        public = fields.Bool(missing=True)
        tls_termination = fields.Bool(missing=False)
        tls_cert = fields.Str(missing=None)
        tls_key = fields.Str(missing=None)
        ingress_address = fields.Str(missing=None)
        ingress_ports = fields.List(fields.Int(), missing=list)

    @classmethod
    def _key(cls, name):
        return 'request_' + name

    def __init__(self, relation, app, response=None, **kwargs):
        self._schema = self._Schema()
        self.relation = relation
        self.app = app
        self.response = response
        for field, value in self._schema.load(kwargs).items():
            setattr(self, field, value)

    @classmethod
    def _read(cls, relation, app, name):
        if cls._key(name) not in relation.data[app]:
            return None
        response = Response._read(relation, app, name)
        request = cls(relation, app, response,
                      **json.loads(relation.data[app][cls._key(name)]))
        if not request.backends:
            # These must default the 'ingress-address' values for the units of
            # the application.
            units = {src.name: src
                     for src in relation.data.keys()
                     if getattr(src, 'app', None) is app}
            for unit_name, unit in sorted(units.items()):
                unit_address = relation.data[unit].get('ingress-address')
                if unit_address:
                    request.backends.append(unit_address)
        return request

    @classmethod
    def _read_all(cls, relation, app):
        prefix = cls._key('')
        for key, value in relation.data[app].items():
            if not key.startswith(cls._key('')):
                continue
            name = key[len(prefix):]
            yield cls._read(relation, app, name)

    def _write(self, relation, app):
        relation.data[app][self._key(self.name)] = self._dumps()

    def _dumps(self):
        serialized = self._schema.dump(self)
        errors = self._schema.validate(serialized)
        if errors:
            raise ValidationError(errors)
        return json.dumps(serialized, sort_keys=True)

    def _update(self, data):
        for field, value in self._schema.load(data).items():
            setattr(self, field, value)

    @property
    def hash(self):
        return md5(self._dumps().encode('utf8')).hexdigest()


class LBBase(Object):
    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)
        self.charm = weakref.proxy(charm)
        self.relation_name = relation_name
        self.state.set_default(hash=None)

        # Future-proof against the need to evolve the relation protocol
        # by ensuring that we agree on a version number before starting.
        # This may or may not be made moot by a future feature in Juju.
        for event in (charm.on[relation_name].relation_created,
                      charm.on.leader_elected,
                      charm.on.upgrade_charm):
            self.framework.observe(event, self._set_version)

    def _set_version(self, event):
        if self.unit.is_leader():
            if hasattr(event, 'relation'):
                relations = [event.relation]
            else:
                relations = self.model.relations.get(self.relation_name, [])
            for relation in relations:
                relation.data[self.app]['version'] = str(VERSION)

    @cached_property
    def relations(self):
        relations = self.model.relations.get(self.relation_name, [])
        return [relation
                for relation in sorted(relations, key=attrgetter('id'))
                if VERSION == relation.data.get(relation.app,
                                                {}).get('version')]

    @property
    def is_changed(self):
        return self.state.hash != self.hash

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
        return self.charm.unit
