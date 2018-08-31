#!/usr/bin/env python

import typing

from .. import Serializer


class Protocol:
    """Base class for all protocol implementations."""

    class Error(Exception):
        """Base class for all exceptions thrown by :py:mod:`arpc`."""

        def __init__(self, code: int = None, message: typing.Optional[str] = None,
                     data: typing.Optional[typing.Any] = None):
            self.code = code
            self.message = message
            self.data = data

    class Request:
        def __init__(self, serializer: Serializer, method: str, uid: typing.Optional[int] = None, args: typing.Optional[list] = None,
                     kwargs: typing.Optional[dict] = None):
            """Creates a new RPCRequest object.

            :return: Request object.
            """
            raise NotImplementedError()

        def serialize(self) -> bytes:
            """Returns a serialization of the request.

            :return: A request to be passed on to a transport.
            """
            raise NotImplementedError()

    class SuccessResponse:
        """RPC call response class.

        Base class for all deriving responses.

        Has an attribute ``result`` containing the result of the RPC call, unless
        an error occured, in which case an attribute ``error`` will contain the
        error message."""

        def __init__(self, serializer: Serializer, uid: int, result: typing.Any):
            """Creates success response object.

            :return: Response object.
            """
            raise NotImplementedError()

        def serialize(self) -> bytes:
            """Returns a serialization of the response.

            :return: A reply to be passed on to a transport.
            """
            raise NotImplementedError()

    class ErrorResponse:
        """RPC call response class.

        Base class for all deriving error responses.

        Has an attribute ``result`` containing the result of the RPC call, unless
        an error occured, in which case an attribute ``error`` will contain the
        error message."""

        def __init__(self, serializer: Serializer, code: int, message: str, uid: typing.Optional[int] = None, data: typing.Any = None):
            """Creates error response object.

            :return: Response object.
            """
            raise NotImplementedError()

        def to_exception(self):
            """Returns a serialization of the response.

            :return: A reply to be passed on to a transport.
            """
            raise NotImplementedError()

        def serialize(self) -> bytes:
            """Returns a serialization of the response.

            :return: A reply to be passed on to a transport.
            """
            raise NotImplementedError()

    class ParseError(Error):
        def __init__(self, message: str = None):
            raise NotImplementedError()

    class InvalidRequestError(Error):
        def __init__(self, message: str = None):
            raise NotImplementedError()

    class MethodNotFoundError(Error):
        def __init__(self, message: str = None):
            raise NotImplementedError()

    class InvalidParamsError(Error):
        def __init__(self, code: int, message: str = None):
            raise NotImplementedError()

    class InternalError(Error):
        def __init__(self, message: str = None):
            raise NotImplementedError()

    def __init__(self, serializer: Serializer):
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

    def create_error_response(self, exc: Exception, request: Request = None) -> ErrorResponse:
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

    def parse_request(self, data: bytes) -> Request:
        """Parses a request given as a string and returns an
        :py:class:`RPCRequest` instance.

        :return: An instanced request.
        """
        raise NotImplementedError()

    def parse_response(self, data: bytes) -> typing.Union[SuccessResponse, ErrorResponse]:
        """Parses a reply and returns an :py:class:`RPCResponse` instance.

        :return: An instanced response.
        """
        raise NotImplementedError()
