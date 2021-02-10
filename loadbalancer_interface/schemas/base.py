import inspect
import json
from hashlib import md5

from marshmallow import (
    missing,
    Schema,
    ValidationError,
)


class SchemaWrapper:
    class _Schema(Schema):
        pass

    def __init__(self):
        self._schema = self._Schema()
        self.version = inspect.getmodule(self).version
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
                if hasattr(field, "_validated"):
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
            return md5(self.dumps().encode("utf8")).hexdigest()
        except ValidationError:
            return None
