#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .. import RPCProtocol, RPCRequest, RPCResponse, RPCErrorResponse, \
    InvalidRequestError, MethodNotFoundError, ServerError, \
    InvalidReplyError, RPCError

from collections import namedtuple, OrderedDict

import json
import six
import inspect
import sys

if 'jsonext' in sys.modules:
    # jsonext was imported before this file, assume the intent is that
    # it is used in place of the regular json encoder.
    import jsonext

    json_dumps = jsonext.dumps
else:
    json_dumps = json.dumps


class FixedErrorMessageMixin(object):
    def __init__(self, *args, **kwargs):
        if not args:
            args = [self.message]
        if 'data' in kwargs:
            self.data = kwargs.pop('data')
        super(FixedErrorMessageMixin, self).__init__(*args, **kwargs)

    def error_respond(self):
        response = JSONSRPCErrorResponse()

        response.error = self.message
        response.unique_id = None
        response._jsonrpc_error_code = self.jsonrpc_error_code
        if hasattr(self, 'data'):
            response.data = self.data
        return response


class JSONRPCParseError(FixedErrorMessageMixin, InvalidRequestError):
    jsonrpc_error_code = -32700
    message = 'Parse error'


class JSONRPCInvalidRequestError(FixedErrorMessageMixin, InvalidRequestError):
    jsonrpc_error_code = -32600
    message = 'Invalid Request'


class JSONRPCMethodNotFoundError(FixedErrorMessageMixin, MethodNotFoundError):
    jsonrpc_error_code = -32601
    message = 'Method not found'


class JSONRPCInvalidParamsError(FixedErrorMessageMixin, InvalidRequestError):
    jsonrpc_error_code = -32602
    message = 'Invalid params'


class JSONRPCInternalError(FixedErrorMessageMixin, InvalidRequestError):
    jsonrpc_error_code = -32603
    message = 'Internal error'


class JSONRPCServerError(FixedErrorMessageMixin, InvalidRequestError):
    jsonrpc_error_code = -32000
    message = ''


class JSONSRPCUnknownClientError(FixedErrorMessageMixin, InvalidRequestError):
    jsonrpc_error_code = -32001
    message = 'Unknown client'


class JSONSRPCSignatureError(FixedErrorMessageMixin, InvalidRequestError):
    jsonrpc_error_code = -32002
    message = 'Signature error'


class JSONSRPCTimestampError(FixedErrorMessageMixin, InvalidRequestError):
    jsonrpc_error_code = -32003
    message = 'Timestamp error'


class JSONSRPCNonceError(FixedErrorMessageMixin, InvalidRequestError):
    jsonrpc_error_code = -32004
    message = 'Nonce error'


class JSONSRPCSuccessResponse(RPCResponse):
    def _to_dict(self):
        return {
            'id': self.unique_id,
            'result': self.result,
            'client': self.client,
            'nonce': self.nonce,
            'timestamp': self.timestamp,
            'sig': self.sig
        }

    def serialize(self):
        return json_dumps(self._to_dict()).encode()


class JSONSRPCErrorResponse(RPCErrorResponse):
    def _to_dict(self):
        msg = {
            'id': self.unique_id,
            'client': self.client,
            'nonce': self.nonce,
            'timestamp': self.timestamp,
            'sig': self.sig,
            'error': {
                'message': str(self.error),
                'code': self._jsonrpc_error_code,
            }
        }
        if hasattr(self, 'data'):
            msg['error']['data'] = self.data
        return msg

    def serialize(self):
        return json_dumps(self._to_dict()).encode()


def _get_code_message_and_data(error):
    assert isinstance(error, (Exception, six.string_types))
    data = None
    if isinstance(error, Exception):
        if hasattr(error, 'jsonrpc_error_code'):
            code = error.jsonrpc_error_code
            msg = str(error)
            try:
                data = error.data
            except AttributeError:
                pass
        elif isinstance(error, InvalidRequestError):
            code = JSONRPCInvalidRequestError.jsonrpc_error_code
            msg = JSONRPCInvalidRequestError.message
        elif isinstance(error, MethodNotFoundError):
            code = JSONRPCMethodNotFoundError.jsonrpc_error_code
            msg = JSONRPCMethodNotFoundError.message
        else:
            # allow exception message to propagate
            code = JSONRPCServerError.jsonrpc_error_code
            if len(error.args) == 2:
                msg = str(error.args[0])
                data = error.args[1]
            else:
                msg = str(error)
    else:
        code = -32000
        msg = error

    return code, msg, data


class JSONSRPCRequest(RPCRequest):
    def error_respond(self, error):
        if self.unique_id is None:
            return None

        response = JSONSRPCErrorResponse()

        code, msg, data = _get_code_message_and_data(error)

        response.error = msg
        response.unique_id = self.unique_id
        response.client = self.client
        response.nonce = None
        response.sig = None
        response.timestamp = None
        response._jsonrpc_error_code = code
        if data:
            response.data = data
        return response

    def respond(self, result):
        if self.unique_id is None:
            return None

        response = JSONSRPCSuccessResponse()

        response.result = result
        response.unique_id = self.unique_id
        response.client = self.client
        response.nonce = None
        response.sig = None
        response.timestamp = None

        return response

    def _to_dict(self):
        jdata = {
            'method': self.method,
            'client': self.client,
            'nonce': self.nonce,
            'timestamp': self.timestamp,
            'sig': self.sig
        }
        if self.args:
            jdata['params'] = json_dumps(self.args)
        if self.kwargs:
            jdata['params'] = json_dumps(self.kwargs)
        if hasattr(self, 'unique_id') and self.unique_id is not None:
            jdata['id'] = self.unique_id
        return jdata

    def serialize(self):
        return json_dumps(self._to_dict()).encode()


class JSONSRPCProtocol(RPCProtocol):
    """JSONS RPC protocol implementation.

    Currently, only version 2.0 is supported."""

    JSONS_RPC_VERSION = "2.0"
    _ALLOWED_REPLY_KEYS = sorted(['id', 'error', 'result', 'client', 'nonce', 'timestamp', 'sig'])
    _ALLOWED_REQUEST_KEYS = sorted(['id', 'method', 'params', 'client', 'nonce', 'timestamp', 'sig'])

    UnknownClientError = JSONSRPCUnknownClientError
    SignatureError = JSONSRPCSignatureError
    TimestampError = JSONSRPCTimestampError
    NonceError = JSONSRPCNonceError

    def __init__(self, *args, **kwargs):
        super(JSONSRPCProtocol, self).__init__(*args, **kwargs)
        self._id_counter = 0

    def _get_unique_id(self):
        self._id_counter += 1
        return self._id_counter

    def create_request(self, method, args=None, kwargs=None, one_way=False, assistant=None):
        if args and kwargs:
            raise InvalidRequestError('Does not support args and kwargs at ' \
                                      'the same time')

        request = JSONSRPCRequest()

        if not one_way:
            request.unique_id = self._get_unique_id()

        request.method = method
        request.args = args
        request.kwargs = kwargs

        return request

    def parse_reply(self, data):
        try:
            rep = json.loads(data)
        except Exception as e:
            raise InvalidReplyError(e)

        for k in six.iterkeys(rep):
            if not k in self._ALLOWED_REPLY_KEYS:
                raise InvalidReplyError('Key not allowed: %s' % k)

        if rep.get('jsonrpc', self.JSONS_RPC_VERSION) != self.JSONS_RPC_VERSION:
            raise InvalidReplyError('Wrong JSONRPC version')

        if 'id' not in rep:
            raise InvalidReplyError('Missing id in response')

        if 'client' not in rep:
            raise InvalidReplyError('Missing client in response')

        if 'nonce' not in rep:
            raise InvalidReplyError('Missing nonce in response')

        if 'timestamp' not in rep:
            raise InvalidReplyError('Missing timestamp in response')

        if 'sig' not in rep:
            raise InvalidReplyError('Missing sig in response')

        if ('error' in rep) == ('result' in rep):
            raise InvalidReplyError(
                'Reply must contain exactly one of result and error.'
            )

        if 'error' in rep:
            response = JSONSRPCErrorResponse()
            error = rep['error']
            response.error = error['message']
            response._jsonrpc_error_code = error['code']
        else:
            response = JSONSRPCSuccessResponse()
            response.result = rep.get('result', None)

        response.unique_id = rep['id']
        response.client = rep['client']
        response.nonce = rep['nonce']
        response.timestamp = rep['timestamp']
        response.sig = rep['sig']

        return response

    def parse_request(self, data):
        try:
            req = json.loads(data)
        except Exception as e:
            raise JSONRPCParseError()

        for k in six.iterkeys(req):
            if not k in self._ALLOWED_REQUEST_KEYS:
                raise JSONRPCInvalidRequestError()

        if req.get('jsonrpc', self.JSONS_RPC_VERSION) != self.JSONS_RPC_VERSION:
            raise JSONRPCInvalidRequestError()

        if not isinstance(req['method'], six.string_types):
            raise JSONRPCInvalidRequestError()

        request = JSONSRPCRequest()
        request.method = str(req['method'])
        request.unique_id = req.get('id', None)
        request.client = req['client']
        request.nonce = req['nonce']
        request.timestamp = req['timestamp']
        request.sig = req['sig']

        params = req.get('params', None)
        if params != None:
            params = json.loads(params, object_pairs_hook=OrderedDict)
            if isinstance(params, list):
                request.args = params
            elif isinstance(params, dict):
                request.kwargs = params
            else:
                raise JSONRPCInvalidParamsError()

        return request

