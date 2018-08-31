# !/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging
import sys

from .. import Serializer

logger = logging.getLogger('arpc.serializers.json')

if 'jsonext' in sys.modules:
    # jsonext was imported before this file, assume the intent is that
    # it is used in place of the regular json encoder.
    import jsonext

    json_dumps = jsonext.dumps
else:
    json_dumps = json.dumps


class JsonSerializer(Serializer):
    """JSON serializer."""

    def serialize(self, message: dict) -> bytes:
        return json_dumps(message)

    def deserialize(self, data: bytes) -> dict:
        return json.loads(data).encode()
