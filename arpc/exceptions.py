import typing


class BaseError(Exception):
    """Base library exception. Shouldn't be used directly."""
    pass


class BaseRpcError(BaseError):
    """Base class for all rpc exceptions. Shouldn't be used directly."""
    pass


class RpcError(BaseRpcError):
    """Base class for all rpc exceptions.

    Should be used for all user-defined exceptions."""

    def __init__(self, code: int, message: str, data: typing.Optional[typing.Any] = None):
        self.__code = code
        self.__message = message
        self.__data = data

    @property
    def code(self):
        return self.__code

    @property
    def message(self):
        return self.__message

    @property
    def data(self):
        return self.__data

    def __str__(self):
        return "Rpc error %s: '%s'" % (self.code, self.message)

    def __repr__(self):
        return "%s(\"%s\")" % (self.__class__.__name__, str(self))


class ParseError(BaseRpcError):
    """Invalid data was received by the server.
    An error occurred on the server while deserialization the client data."""
    pass


class InvalidRequestError(BaseRpcError):
    """The data sent is not a valid Request object."""
    pass


class MethodNotFoundError(BaseRpcError):
    """The method does not exist / is not available."""
    pass


class InvalidParamsError(BaseRpcError):
    """Invalid method parameter(s)."""
    pass


class InternalError(BaseRpcError):
    """Internal error."""
    pass


class ServerError(BaseRpcError):
    """Server error."""
    pass


class RequestTimeoutError(BaseError):
    """Request to server was timed out."""
    pass


class ServerReplyError(BaseError):
    """Invalid data was received from the server."""
    pass
