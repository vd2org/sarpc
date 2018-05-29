#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pickle

import six

from .. import RPCProtocol, RPCErrorResponse, \
    InvalidRequestError, MethodNotFoundError, InvalidReplyError, RPCRequest, RPCResponse


class FixedErrorMessageMixin(object):
    def __init__(self, *args, **kwargs):
        if not args:
            args = [self.message]
        if 'data' in kwargs:
            self.data = kwargs.pop('data')
        super(FixedErrorMessageMixin, self).__init__(*args, **kwargs)

    def error_respond(self):
        response = PickleRPCErrorResponse()

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


class PickleRPCSuccessResponse(RPCResponse):
    def _to_dict(self):
        return {
            'id': self.unique_id,
            'result': self.result
        }

    def serialize(self, pickle_protocol=None):
        return pickle.dumps(self._to_dict(), protocol=pickle_protocol)


class PickleRPCErrorResponse(RPCErrorResponse):
    def _to_dict(self):
        msg = {
            'id': self.unique_id,
            'error': {
                'message': str(self.error),
                'code': self._jsonrpc_error_code
            }
        }
        if hasattr(self, 'data'):
            msg['error']['data'] = self.data
        return msg

    def serialize(self, pickle_protocol=None):
        return pickle.dumps(self._to_dict(), protocol=pickle_protocol)


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


class Request(RPCRequest):
    def error_respond(self, error):
        if self.unique_id is None:
            return None

        response = PickleRPCErrorResponse()

        code, msg, data = _get_code_message_and_data(error)

        response.error = msg
        response.unique_id = self.unique_id
        response._jsonrpc_error_code = code
        if data:
            response.data = data
        return response

    def respond(self, result):
        if self.unique_id is None:
            return None

        response = PickleRPCSuccessResponse()

        response.result = result
        response.unique_id = self.unique_id

        return response

    def _to_dict(self):
        jdata = {
            'method': self.method,
        }
        if self.args:
            jdata['args'] = self.args
        if self.kwargs:
            jdata['kwargs'] = self.kwargs
        if hasattr(self, 'unique_id') and self.unique_id is not None:
            jdata['id'] = self.unique_id
        return jdata

    def serialize(self, pickle_protocol=None):
        return pickle.dumps(self._to_dict(), protocol=pickle_protocol)


class PickleRPCProtocol(RPCProtocol):
    """PickleRPC protocol implementation."""

    PICKLE_RPC_VERSION = "1.0"
    _ALLOWED_REPLY_KEYS = sorted(['id', 'version', 'error', 'result'])
    _ALLOWED_REQUEST_KEYS = sorted(['id', 'version', 'method', 'args', 'kwargs'])

    def __init__(self, *args, pickle_protocol=None, **kwargs):
        super(PickleRPCProtocol, self).__init__(*args, **kwargs)
        self._id_counter = 0
        self.pickle_protocol = pickle_protocol

    def _get_unique_id(self):
        self._id_counter += 1
        return self._id_counter

    def create_request(self, method, args=None, kwargs=None, one_way=False):
        request = Request()

        if not one_way:
            request.unique_id = self._get_unique_id()

        request.method = method
        request.args = args
        request.kwargs = kwargs

        return request

    def parse_reply(self, data):
        try:
            rep = pickle.loads(data)
        except Exception as e:
            raise InvalidReplyError(e)

        for k in six.iterkeys(rep):
            if not k in self._ALLOWED_REPLY_KEYS:
                raise InvalidReplyError('Key not allowed: %s' % k)

        if rep.get('version', self.PICKLE_RPC_VERSION) != self.PICKLE_RPC_VERSION:
            raise InvalidReplyError('Wrong PickleRPC version')

        if not 'id' in rep:
            raise InvalidReplyError('Missing id in response')

        if ('error' in rep) == ('result' in rep):
            raise InvalidReplyError('Reply must contain exactly one of result and error.')

        if 'error' in rep:
            response = PickleRPCErrorResponse()
            error = rep['error']
            response.error = error['message']
            response._jsonrpc_error_code = error['code']
        else:
            response = PickleRPCSuccessResponse()
            response.result = rep.get('result', None)

        response.unique_id = rep['id']

        return response

    def parse_request(self, data):
        try:
            req = pickle.loads(data)
        except Exception as e:
            raise JSONRPCParseError()

        for k in six.iterkeys(req):
            if not k in self._ALLOWED_REQUEST_KEYS:
                raise JSONRPCInvalidRequestError()

        if req.get('version', self.PICKLE_RPC_VERSION) != self.PICKLE_RPC_VERSION:
            raise JSONRPCInvalidRequestError()

        request = Request()
        request.method = str(req['method'])
        request.unique_id = req.get('id', None)

        request.args = req.get('args', [])
        if request.args and not isinstance(request.args, (list, tuple)):
            raise JSONRPCInvalidParamsError()
        request.kwargs = req.get('kwargs', {})
        if request.kwargs and not isinstance(request.kwargs, dict):
            raise JSONRPCInvalidParamsError()

        return request
