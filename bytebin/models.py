import uuid


class ConfigurationError(Exception):
    pass


class NotFound(Exception):
    pass


class RedisModel:
    NotFound = NotFound

    @classmethod
    def set_connection(cls, redis_connection):
        if getattr(cls, '_redis_connection', None):
            raise ConfigurationError('Connection already set')
        cls._redis_connection = redis_connection

    @classmethod
    def find(cls, key):
        attrs = cls._redis_connection.hgetall(key)
        if not attrs:
            raise cls.NotFound(key)
        return cls(key=key, **attrs)

    def __init__(self, key=None, **kwargs):
        self.key = key
        self.__dict__.update(**kwargs)

    def save(self, timeout=60 * 60):
        """Save paste in database

        If paste has key assigned, paste will be updated only if already stored
        in database. Otherwise, unique key will be generated.
        """
        rd = self._redis_connection

        if not self.key:
            self.key = str(uuid.uuid4())
        for name, value in self.__dict__.items():
            if name.startswith('_'):
                continue
            rd.hset(self.key, name, getattr(self, name))
        rd.hset(self.key, '_type', type(self).__name__)
        rd.expire(self.key, timeout)
        return self

    def to_json(self):
        properties = self.__dict__.items()
        return dict({k:v for (k, v) in properties if not k.startswith('_')})

    def delete(self):
        """Delete paste from database.

        If paste does not exist in database, :exc:`NotFound` exception will be
        raised.
        """
        if not self.key:
            raise self.NotFound("instance does not have key")
        if not self._redis_connection.delete(self.key):
            raise self.NotFound("not stored")
        self.key = None
        return self


class Paste(RedisModel):
    pass
