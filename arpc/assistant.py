#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import base64
import six
import inspect
import time
import hmac
import hashlib
import secrets

from .exc import RPCError
from .protocols import RPCErrorResponse

if 'jsonext' in sys.modules:
    # jsonext was imported before this file, assume the intent is that
    # it is used in place of the regular json encoder.
    import jsonext

    json_dumps = jsonext.dumps
else:
    json_dumps = json.dumps

NONCE_LENGTH = None
MAX_TIMESTAMP_DELTA = 3600


class RPCAssistant(object):
    """Authentication and nonce manager."""

    async def client_get_client(self):
        raise NotImplementedError

    async def client_get_key(self):
        raise NotImplementedError

    async def client_get_request_nonce(self):
        raise NotImplementedError

    async def client_check_response_nonce(self, nonce):
        raise NotImplementedError

    async def server_get_client_key(self, client):
        raise NotImplementedError

    async def server_check_request_nonce(self, client, nonce):
        raise NotImplementedError

    async def server_get_response_nonce(self, client):
        raise NotImplementedError

    async def client_sign_request(self, request):
        """Assign nonce and signs request.

        :param request: The request that will be signed.
        """

        request.nonce = await self.client_get_request_nonce()
        request.timestamp = int(time.time())
        request.client = await self.client_get_client()

        key = await self.client_get_key()

        msg = self._req_msg(request)

        request.sig = self._sign(key, msg)

    async def client_check_response(self, response):
        """Check server response nonce, timestamp and sig.

        :param response: The response that will be checked.
        """

        if response.client != await self.client_get_client():
            raise RPCError('Error while checking response: client mismatch.')

        key = await self.client_get_key()

        if isinstance(response, RPCErrorResponse):
            msg = self._error_rep_msg(response)
        else:
            msg = self._rep_msg(response)

        if not secrets.compare_digest(response.sig, self._sign(key, msg)):
            raise RPCError('Error while checking response: sig error.')

        if not await self.client_check_response_nonce(response.nonce):
            raise RPCError('Error while checking response: nonce error.')

        if abs(int(time.time()) - response.timestamp) > MAX_TIMESTAMP_DELTA:
            raise RPCError('Error while checking response: timestamp error.')

    async def server_check_request(self, protocol, request):
        """Check request nonce, timestamp and sig.

        :param protocol: The used protocol.
        :param request: The request that will be checked.
        """

        key = await self.server_get_client_key(request.client)

        if not key:
            raise protocol.UnknownClientError

        if abs(int(time.time()) - request.timestamp) > MAX_TIMESTAMP_DELTA:
            raise protocol.TimestampError

        if not await self.server_check_request_nonce(request.client, request.nonce):
            raise protocol.NonceError

        if not secrets.compare_digest(self._sign(key, self._req_msg(request)), request.sig):
            raise protocol.SignatureError

    async def server_sign_response(self, response):
        response.nonce = await self.server_get_response_nonce(response.client)
        response.timestamp = int(time.time())

        key = await self.server_get_client_key(response.client)

        if not key:
            response.sig = ''
            return

        if isinstance(response, RPCErrorResponse):
            msg = self._error_rep_msg(response)
        else:
            msg = self._rep_msg(response)

        response.sig = self._sign(key, msg)

    def _sign(self, key, msg):
        return base64.b64encode(hmac.new(key.encode(), msg.encode(), digestmod=hashlib.sha256).digest()).decode()

    def _req_msg(self, req):
        d = req._to_dict()
        if 'params' in d:
            params = json_dumps(d['params'])
        else:
            params = ''

        s = str(d['client']) + str(d['method'])
        if 'id' in d:
            s = s + str(d['id'])

        return s + d['nonce'] + str(d['timestamp']) + params

    def _rep_msg(self, rep):
        d = rep._to_dict()
        result = json_dumps(d['result'])

        return str(d['client']) + str(d['id']) + d['nonce'] + str(d['timestamp']) + result

    def _error_rep_msg(self, rep):
        d = rep._to_dict()
        error = json_dumps(d['error'])

        return str(d['client']) + str(d['id']) + d['nonce'] + str(d['timestamp']) + error


class RPCClientAssistant(RPCAssistant):
    def __init__(self, client, key):
        self.client = client
        self.key = key
        self._reply_nonces = dict()

    async def client_get_client(self):
        return self.client

    async def client_get_key(self):
        return self.key

    async def client_get_request_nonce(self):
        return base64.b85encode(secrets.token_bytes(NONCE_LENGTH)).decode()

    async def client_check_response_nonce(self, nonce):
        for n in self._reply_nonces.keys():
            if abs(int(time.time()) - self._reply_nonces[n]) > MAX_TIMESTAMP_DELTA:
                del self._reply_nonces[n]

        if nonce in self._reply_nonces:
            return False
        else:
            self._reply_nonces[nonce] = int(time.time())
            return True

    async def server_get_client_key(self, client):
        raise NotImplementedError

    async def server_check_request_nonce(self, client, nonce):
        raise NotImplementedError

    async def server_get_response_nonce(self, client):
        raise NotImplementedError


class RPCServerAssistant(RPCAssistant):
    def __init__(self, clients):
        self.clients = clients
        self._request_nonces = dict()

    async def server_get_client_key(self, client):
        return self.clients.get(client)

    async def server_check_request_nonce(self, client, nonce):
        if client not in self._request_nonces:
            self._request_nonces[client] = dict()

        nonces = self._request_nonces[client]

        for n in nonces.copy().keys():
            if abs(int(time.time()) - nonces[n]) > MAX_TIMESTAMP_DELTA:
                del nonces[n]

        if nonce in nonces:
            return False
        else:
            nonces[nonce] = int(time.time())
            return True

    async def server_get_response_nonce(self, client):
        return base64.b85encode(secrets.token_bytes(NONCE_LENGTH)).decode()

    async def client_get_client(self):
        raise NotImplementedError

    async def client_get_key(self):
        raise NotImplementedError

    async def client_get_request_nonce(self):
        raise NotImplementedError

    async def client_check_response_nonce(self, nonce):
        raise NotImplementedError
