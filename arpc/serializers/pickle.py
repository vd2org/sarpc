# !/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import pickle

from .. import Serializer

logger = logging.getLogger('arpc.serializers.pickle')


class PickleSerializer(Serializer):
    """Pickle serializer."""

    def __init__(self, protocol=None, fix_imports=True):
        self.protocol = protocol
        self.fix_imports = fix_imports

    def serialize(self, message: dict) -> bytes:
        return pickle.dumps(message, self.protocol, fix_imports=self.fix_imports)

    def deserialize(self, data: bytes) -> dict:
        return pickle.loads(data, fix_imports=self.fix_imports)
