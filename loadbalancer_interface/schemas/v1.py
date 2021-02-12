import json
from enum import Enum

from marshmallow import (
    Schema,
    fields,
    validates_schema,
    ValidationError,
)
from marshmallow_enum import EnumField

from .base import SchemaWrapper


version = 1


class Protocols(Enum):
    tcp = "tcp"
    udp = "udp"
    http = "http"
    https = "https"

    def __str__(self):
        return self.value


class ErrorTypes(Enum):
    unsupported = "unsupported"
    provider_error = "provider error"

    def __str__(self):
        return self.value


class Response(SchemaWrapper):
    error_types = ErrorTypes

    class _Schema(Schema):
        error = EnumField(ErrorTypes, missing=None)
        error_message = fields.Str(missing=None)
        error_fields = fields.Dict(key=fields.Str, value=fields.Str, missing=dict)
        address = fields.Str(missing=None)
        received_hash = fields.Str(missing=None)

        @validates_schema
        def _validate(self, data, **kwargs):
            if not data["error"] and not data["address"]:
                raise ValidationError("address required on success")
            if data["error"] and not (data["error_message"] or data["error_fields"]):
                raise ValidationError(
                    "error_message or error_fields required on failure"
                )
            request_fields = Request._Schema().fields
            unknown_fields = data["error_fields"].keys() - request_fields.keys()
            if unknown_fields:
                s = "s" if len(unknown_fields) > 1 else ""
                raise ValidationError(
                    {
                        "error_fields": "Unknown field{}: {}".format(
                            s, ", ".join(unknown_fields)
                        )
                    }
                )

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
        protocol = EnumField(Protocols, by_value=True, required=True)
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
    protocols = Protocols

    class _Schema(Schema):
        protocol = EnumField(Protocols, by_value=True, required=True)
        backends = fields.List(fields.Str(), missing=list)
        port_mapping = fields.Dict(
            keys=fields.Int(), values=fields.Int(), required=True
        )
        algorithm = fields.List(fields.Str(), missing=list)
        sticky = fields.Bool(missing=False)
        health_checks = fields.List(HealthCheckField, missing=list)
        public = fields.Bool(missing=True)
        tls_termination = fields.Bool(missing=False)
        tls_cert = fields.Str(missing=None)
        tls_key = fields.Str(missing=None)
        ingress_address = fields.Str(missing=None)
        sent_hash = fields.Str(missing=None)

    @classmethod
    def _from_id(cls, req_id, relations):
        """Return an empty Request with the given ID.

        This represents an unknown or removed request.
        """
        name, rel_id = req_id.split(":")
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
            self._id = "{}:{}".format(self.relation.id, self.name)
        return self._id

    @classmethod
    def loads(cls, name, request_sdata, response_sdata=None):
        self = cls(name)
        self._update(json.loads(request_sdata))
        if response_sdata:
            self.response._update(json.loads(response_sdata))
        return self

    def add_health_check(self, **kwargs):
        """Create a HealthCheck and add it to the list."""
        health_check = HealthCheck()._update(kwargs)
        self.health_checks.append(health_check)
        return health_check
