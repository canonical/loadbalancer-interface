import json
from hashlib import md5

from marshmallow import (
    Schema,
    fields,
    validates_schema,
    ValidationError,
    missing,
)


version = 1


class SchemaWrapper:
    class _Schema(Schema):
        pass

    def __init__(self):
        self._schema = self._Schema()
        self.version = version
        for field_name, field in self._schema.fields.items():
            if field.missing is not missing:
                value = field.missing
                if callable(value):
                    value = value()
            else:
                value = None
            setattr(self, field_name, value)

    def _update(self, data=None, **kwdata):
        if data is None:
            data = {}
        data.update(kwdata)
        for field, value in self._schema.load(data).items():
            setattr(self, field, value)
        return self

    def dump(self):
        # We have to manually validate every field first, or serialization can
        # can fail and we won't know which field it failed on.
        for field_name, field in self._schema.fields.items():
            value = getattr(self, field_name, None)
            try:
                if hasattr(field, '_validated'):
                    # For some reason, some field types do their validation in
                    # a `_validated` method, rather than in the `_validate`
                    # from the base Field class. For those, calling `_validate`
                    # doesn't actually do any validation.
                    field._validated(value)
                else:
                    field._validate(value)
                field._validate_missing(value)
            except ValidationError as e:
                raise ValidationError({field_name: e.messages}) from e
        serialized = self._schema.dump(self)
        # Then we have to validate the serialized data again to catch any
        # schema-level validation issues.
        errors = self._schema.validate(serialized)
        if errors:
            raise ValidationError(errors)
        return serialized

    def dumps(self):
        return json.dumps(self.dump(), sort_keys=True)

    @property
    def hash(self):
        try:
            return md5(self.dumps().encode('utf8')).hexdigest()
        except ValidationError:
            return None


class Response(SchemaWrapper):
    class _Schema(Schema):
        success = fields.Bool(required=True)
        message = fields.Str(missing=None)
        address = fields.Str(required=True)
        request_hash = fields.Str(missing=None)

        @validates_schema
        def _validate(self, data, **kwargs):
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

    def __init__(self, name):
        super().__init__()
        self._name = name
        # On the provider side, requests need to track which relation they
        # came from to know where to send the response.
        self.relation = None
        self.response = Response(self)

    @property
    def name(self):
        return self._name

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
