class Serializer:
    """Base class for all serializers."""

    def serialize(self, message: dict) -> bytes:
        """Serialize message."""
        raise NotImplementedError()

    def deserialize(self, data: bytes) -> dict:
        """Deserialize message."""
        raise NotImplementedError()
