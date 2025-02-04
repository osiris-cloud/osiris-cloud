from django.db import models
from uuid_utils import uuid7, UUID


def generate_uuid7() -> str:
    return str(uuid7())


class UUID7StringField(models.CharField):
    description = "Field for storing UUID version 7"

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 36
        kwargs['unique'] = True
        kwargs['default'] = generate_uuid7
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if isinstance(value, str):
            try:
                return str(UUID(value))
            except ValueError:
                pass
            raise self.model.DoesNotExist("UUID7 value not found")
        return value

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        if isinstance(value, str):
            return value
        raise self.model.DoesNotExist("UUID7 value not found")
