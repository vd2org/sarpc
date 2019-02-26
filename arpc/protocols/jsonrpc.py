import typing

from .. import exceptions
from ..protocol import Protocol, Request, SuccessResponse, ErrorResponse

PARSE_ERROR_CODE = -32700
INVALID_REQUEST_CODE = -32600
METHOD_NOT_FOUND_CODE = -32601
INVALID_PARAMS_CODE = -32602
INTERNAL_ERROR_CODE = -32603

MIN_VALID_SERVER_ERROR_CODE = -32099
MAX_VALID_SERVER_ERROR_CODE = -32000


class JSONRPCParseError(exceptions.ParseError, exceptions.RpcError):
    def __init__(self, message="Parse error", data=None):
        super().__init__(PARSE_ERROR_CODE, message, data=data)


class JSONRPCInvalidRequestError(exceptions.InvalidRequestError, exceptions.RpcError):
    def __init__(self, message="Invalid Request", data=None):
        super().__init__(INVALID_REQUEST_CODE, message, data=data)


class JSONRPCMethodNotFoundError(exceptions.MethodNotFoundError, exceptions.RpcError):
    def __init__(self, message="Method not found", data=None):
        super().__init__(METHOD_NOT_FOUND_CODE, message, data=data)


class JSONRPCInvalidParamsError(exceptions.InvalidParamsError, exceptions.RpcError):
    def __init__(self, message="Invalid params", data=None):
        super().__init__(INVALID_PARAMS_CODE, message, data)


class JSONRPCInternalError(exceptions.InternalError, exceptions.RpcError):
    def __init__(self, message="Internal error", data=None):
        super().__init__(INTERNAL_ERROR_CODE, message, data=data)


errors_by_code = {
    PARSE_ERROR_CODE: JSONRPCParseError,
    INVALID_REQUEST_CODE: JSONRPCInvalidRequestError,
    METHOD_NOT_FOUND_CODE: JSONRPCMethodNotFoundError,
    INVALID_PARAMS_CODE: JSONRPCInvalidParamsError,
    INTERNAL_ERROR_CODE: JSONRPCInternalError,
}


class JSONRPCServerError(exceptions.ServerError, exceptions.RpcError):
    @classmethod
    def check_valid(cls, code):
        return MIN_VALID_SERVER_ERROR_CODE <= code <= MAX_VALID_SERVER_ERROR_CODE

    def __init__(self, code: int = MAX_VALID_SERVER_ERROR_CODE):
        if not self.check_valid(code):
            raise ValueError("Wrong code for Server error!")
        super().__init__(code, "Server error")


class JSONRPCInvalidRequestError(exceptions.BaseError):
    pass


class JSONRPCRequest(Request):
    def __init__(self, method: str, uid: typing.Optional[typing.Any] = None,
                 args: typing.Optional[list] = None, kwargs: typing.Optional[dict] = None):

        if args and kwargs:
            raise JSONRPCInvalidRequestError('Does not support args and kwargs at the same time.')
        super().__init__(method, uid, args, kwargs)

    def to_data(self):
        data = {
            'jsonrpc': JSONRPCProtocol.JSON_RPC_VERSION,
            'method': self.method,
        }
        if self.args:
            data['params'] = self.args
        if self.kwargs:
            data['params'] = self.kwargs
        if self.uid is not None:
            data['id'] = self.uid

        return data


class JSONRPCSuccessResponse(SuccessResponse):
    def to_data(self):
        return {
            'jsonrpc': JSONRPCProtocol.JSON_RPC_VERSION,
            'id': self.uid,
            'result': self.result
        }


class JSONRPCErrorResponse(ErrorResponse):
    def to_exception(self):
        error = errors_by_code.get(self.code)
        if not error and JSONRPCServerError.check_valid(self.code):
            error = JSONRPCServerError(self.code)
        if not error:
            error = exceptions.RpcError(self.code, self.message, self.data)
        return error

    def to_data(self):
        data = {
            'jsonrpc': JSONRPCProtocol.JSON_RPC_VERSION,
            'id': self.uid,
            'error': {
                'code': self.code,
                'message': self.message,
            }
        }
        if self.data:
            data['error']['data'] = self.data

        return data


class JSONRPCProtocol(Protocol):
    """JSONRPC version 2.0 protocol implementation."""

    JSON_RPC_VERSION = "2.0"
    _ALLOWED_REPLY_KEYS = sorted(['id', 'jsonrpc', 'error', 'result'])
    _ALLOWED_REQUEST_KEYS = sorted(['id', 'jsonrpc', 'method', 'params'])

    def __init__(self, counter: int = 0):
        """Creates new protocol object.

        :type counter: start request id counter value
        """
        self._counter = counter

    def _get_uid(self):
        self._counter += 1
        return self._counter

    def create_request(self, method: str, args: list = None, kwargs: dict = None,
                       one_way: bool = False) -> JSONRPCRequest:

        if args and kwargs:
            raise JSONRPCInvalidRequestError('Does not support args and kwargs at the same time.')

        uid = None if one_way else self._get_uid()

        return JSONRPCRequest(method, uid, args, kwargs)

    def create_response(self, request: Request, reply: typing.Any) -> JSONRPCSuccessResponse:
        return JSONRPCSuccessResponse(request.uid, reply)

    def create_error_response(self, exception: Exception,
                              request: typing.Optional[Request] = None) -> JSONRPCErrorResponse:
        uid = request.uid if request else None
        if isinstance(exception, exceptions.RpcError):
            pass
        elif isinstance(exception, exceptions.ParseError):
            exception = JSONRPCParseError()
        elif isinstance(exception, exceptions.InvalidRequestError):
            exception = JSONRPCInvalidRequestError()
        elif isinstance(exception, exceptions.MethodNotFoundError):
            exception = JSONRPCMethodNotFoundError()
        elif isinstance(exception, exceptions.InvalidParamsError):
            print(str(exception))
            exception = JSONRPCInvalidParamsError(data=str(exception))
        elif isinstance(exception, exceptions.InternalError):
            exception = JSONRPCInternalError()
        elif isinstance(exception, exceptions.ServerError):
            exception = JSONRPCServerError()
        else:
            exception = JSONRPCInternalError()

        return JSONRPCErrorResponse(uid, exception.code, exception.message, exception.data)

    def parse_request(self, data: dict) -> JSONRPCRequest:
        for k in data.keys():
            if k not in self._ALLOWED_REQUEST_KEYS:
                raise JSONRPCInvalidRequestError('Key not allowed: %s' % k)

        if data.get('jsonrpc') != self.JSON_RPC_VERSION:
            raise JSONRPCInvalidRequestError("Wrong or missing jsonrpc version")

        method = data['method']
        if not isinstance(method, str):
            raise JSONRPCInvalidRequestError("method must be str")

        uid = data.get('id')
        if uid and not isinstance(uid, int):
            raise JSONRPCInvalidRequestError("id must be int")

        params = data.get('params')
        args = list()
        kwargs = dict()
        if isinstance(params, list):
            args = params
        elif isinstance(params, dict):
            kwargs = params
        else:
            raise JSONRPCInvalidParamsError("params must be list or dict")

        return JSONRPCRequest(method, uid, args, kwargs)

    def parse_response(self, data: dict) -> typing.Union[JSONRPCSuccessResponse, JSONRPCErrorResponse]:
        for k in data.keys():
            if k not in self._ALLOWED_REPLY_KEYS:
                raise exceptions.ServerReplyError('Key not allowed: %s' % k)

        if data.get('jsonrpc') != self.JSON_RPC_VERSION:
            raise exceptions.ServerReplyError("Wrong or missing jsonrpc version")

        uid = data.get('id')
        if uid and not isinstance(uid, (int, str)):
            raise exceptions.ServerReplyError("id must be int or str or None")

        if ('error' in data) == ('result' in data):
            raise exceptions.ServerReplyError('Reply must contain exactly one of result and error.')

        if 'result' in data:
            return JSONRPCSuccessResponse(uid, data['result'])
        else:
            error = data['error']

            code = error.get('code')
            if not isinstance(code, int):
                raise exceptions.ServerReplyError("error.code must be int")

            message = error.get('message')
            if not isinstance(message, str):
                raise exceptions.ServerReplyError("error.message must be str")

            data = error.get('data')

            return JSONRPCErrorResponse(uid, code, message, data)
