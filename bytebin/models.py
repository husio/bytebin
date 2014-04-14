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


class Paste(RedisModel):
    def __init__(self, content, key=None):
        self.content = content
        self.key = key

    @classmethod
    def find(cls, key):
        content = cls._redis_connection.get(key)
        if content is None:
            raise cls.NotFound(key)
        return cls(content=content, key=key)

    def save(self, timeout=60 * 60):
        """Save paste in database

        If paste has key assigned, paste will be updated only if already stored
        in database. Otherwise, unique key will be generated.
        """
        r = self._redis_connection

        if self.key:
            if not r.set(self.key, self.content, xx=True):
                raise self.NotFound("not stored")

        while True:
            key = str(uuid.uuid4())
            if r.set(key, self.content, nx=True, ex=timeout):
                self.key = key
                break
        return self

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
