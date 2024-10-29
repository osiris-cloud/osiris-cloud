from django.db import models
from uuid_utils import uuid7, UUID


class UUID7StringField(models.CharField):
    description = "Field for storing UUID version 7"

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 36
        kwargs['unique'] = True
        kwargs['default'] = lambda: str(uuid7())
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if isinstance(value, str):
            try:
                return str(UUID(value))
            except ValueError:
                pass
            raise ValueError(f"{value} is not a valid UUID7.")
        return value

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        if isinstance(value, str):
            return value
        raise ValueError(f"{value} is not a valid UUID7.")
