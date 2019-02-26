import typing

from .exceptions import RpcError


class Request:
    def __init__(self, method: str, uid: typing.Union[int, str, None] = None,
                 args: typing.Optional[list] = None, kwargs: typing.Optional[dict] = None):
        """Base class for all Request objects.

        :return: Request object.
        """
        self.__method = method
        self.__uid = uid
        self.__args = args
        self.__kwargs = kwargs

    @property
    def method(self):
        return self.__method

    @property
    def uid(self):
        return self.__uid

    @property
    def args(self):
        return self.__args

    @property
    def kwargs(self):
        return self.__kwargs

    def to_data(self) -> dict:
        """Returns dict form of the request.

        :return: A request to be passed on to a serializer.
        """
        raise NotImplementedError()


class Response:
    def to_data(self) -> dict:
        """Returns a dict form of the response.

        :return: A reply to be passed on to a transport.
        """
        raise NotImplementedError()


class SuccessResponse(Response):
    """RPC call response class.

    Base class for all deriving responses.

    Has an attribute ``result`` containing the result of the RPC call, unless
    an error occured, in which case an attribute ``error`` will contain the
    error message."""

    def __init__(self, uid: int, result: typing.Any):
        """Creates success response object.

        :return: Response object.
        """
        self.__uid = uid
        self.__result = result

    @property
    def uid(self):
        return self.__uid

    @property
    def result(self):
        return self.__result


class ErrorResponse(Response):
    """RPC call response class.

    Base class for all deriving error responses.

    Has an attribute ``result`` containing the result of the RPC call, unless
    an error occured, in which case an attribute ``error`` will contain the
    error message."""

    def __init__(self, uid: typing.Union[str, int, None], code: int, message: str,
                 data: typing.Any = None):
        """Creates error response object.

        :return: Response object.
        """
        self.__uid = uid
        self.__code = code
        self.__message = message
        self.__data = data

    @property
    def uid(self):
        return self.__uid

    @property
    def code(self):
        return self.__code

    @property
    def message(self):
        return self.__message

    @property
    def data(self):
        return self.__data

    def to_exception(self) -> RpcError:
        """Creates exception from ErrorResponse.

        :return: A exception corresponding ErrorResponse.
        """
        raise NotImplementedError()


class Protocol:
    """Base class for all protocol implementations."""

    def __init__(self):
        raise NotImplementedError()

    def create_response(self, request: Request, reply: typing.Any) -> SuccessResponse:
        """Creates a new RPCRequest object.

        It is up to the implementing protocol whether or not ``args``,
        ``kwargs``, one of these, both at once or none of them are supported.

        :param request:
        :param method: The method name to invoke.
        :param args: The positional arguments to call the method with.
        :param kwargs: The keyword arguments to call the method with.
        :param one_way: The request is an update, i.e. it does not expect a
                        reply.
        :return: A new :py:class:`~tinyrpc.RPCRequest` instance.
        """
        raise NotImplementedError()

    def create_request(self, method: str, args: list = None,
                       kwargs: dict = None, one_way: bool = False) -> Request:
        """Creates a new RPCRequest object.

        It is up to the implementing protocol whether or not ``args``,
        ``kwargs``, one of these, both at once or none of them are supported.

        :param uid:
        :param method: The method name to invoke.
        :param args: The positional arguments to call the method with.
        :param kwargs: The keyword arguments to call the method with.
        :param one_way: The request is an update, i.e. it does not expect a
                        reply.
        :return: A new :py:class:`~tinyrpc.RPCRequest` instance.
        """
        raise NotImplementedError()

    def create_error_response(self, exc: Exception, request: typing.Optional[Request] = None) -> ErrorResponse:
        """Creates a new RPCRequest object.

        It is up to the implementing protocol whether or not ``args``,
        ``kwargs``, one of these, both at once or none of them are supported.

        :param method: The method name to invoke.
        :param args: The positional arguments to call the method with.
        :param kwargs: The keyword arguments to call the method with.
        :param one_way: The request is an update, i.e. it does not expect a
                        reply.
        :return: A new :py:class:`~tinyrpc.RPCRequest` instance.
        """
        raise NotImplementedError()

    def parse_request(self, data: dict) -> Request:
        """Parses a request given as a string and returns an
        :py:class:`RPCRequest` instance.

        :return: An instanced request.
        """
        raise NotImplementedError()

    def parse_response(self, data: dict) -> typing.Union[SuccessResponse, ErrorResponse]:
        """Parses a reply and returns an :py:class:`RPCResponse` instance.

        :return: An instanced response.
        """
        raise NotImplementedError()
