import json

from marshmallow import (
    Schema,
    fields,
    validates_schema,
    ValidationError,
)

from .base import SchemaWrapper


version = 1


class Response(SchemaWrapper):
    class _Schema(Schema):
        success = fields.Bool(required=True)
        message = fields.Str(missing=None)
        address = fields.Str(missing=None)
        received_hash = fields.Str(missing=None)

        @validates_schema
        def _validate(self, data, **kwargs):
            if data['success'] and not data['address']:
                raise ValidationError('address required on success')
            if not data['success'] and not data['message']:
                raise ValidationError('message required on failure')

    def __init__(self, request):
        super().__init__()
        self._name = request.name

    @property
    def name(self):
        return self._name

    def __bool__(self):
        return self.hash is not None


class HealthCheck(SchemaWrapper):
    class _Schema(Schema):
        traffic_type = fields.Str(required=True)
        port = fields.Int(required=True)
        path = fields.Str(missing=None)
        interval = fields.Int(missing=30)
        retries = fields.Int(missing=3)


class HealthCheckField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        return value._schema.dump(value)

    def _deserialize(self, value, attr, data, **kwargs):
        if isinstance(value, HealthCheck):
            return value
        return HealthCheck()._update(value)


class Request(SchemaWrapper):
    class _Schema(Schema):
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
        sent_hash = fields.Str(missing=None)

    @classmethod
    def _from_id(cls, req_id, relations):
        """ Return an empty Request with the given ID.

        This represents an unknown or removed request.
        """
        name, rel_id = req_id.split(':')
        request = cls(name)
        request._id = req_id
        for relation in relations:
            if relation.id == rel_id:
                request.relation = relation
                break
        return request

    def __init__(self, name):
        super().__init__()
        self._name = name
        self._id = None
        # On the provider side, requests need to track which relation they
        # came from to know where to send the response.
        self.relation = None
        self.response = Response(self)

    @property
    def name(self):
        return self._name

    @property
    def id(self):
        if self._id is None:
            if self.relation is None:
                return None
            self._id = '{}:{}'.format(self.relation.id, self.name)
        return self._id

    @classmethod
    def loads(cls, name, request_sdata, response_sdata=None):
        self = cls(name)
        self._update(json.loads(request_sdata))
        if response_sdata:
            self.response._update(json.loads(response_sdata))
        return self

    def add_health_check(self, **kwargs):
        """ Create a HealthCheck and add it to the list.
        """
        health_check = HealthCheck()._update(kwargs)
        self.health_checks.append(health_check)
        return health_check
