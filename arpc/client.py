#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .protocol import Protocol, ErrorResponse
from .transport import ClientTransport
from .serializer import Serializer


class Client:
    """Client for making RPC calls to connected servers.

    :param protocol: An :py:class:`~tinyrpc.RPCProtocol` instance.
    :param transport: A :py:class:`~tinyrpc.transports.ClientTransport`
                      instance.
    """

    def __init__(self, protocol: Protocol, serializer: Serializer, transport: ClientTransport):
        self.__protocol = protocol
        self.__serializer = serializer
        self.__transport = transport
        self.__active = False

    @property
    def protocol(self):
        return self.__protocol

    @property
    def serializer(self):
        return self.__serializer

    @property
    def transport(self):
        return self.__transport

    @property
    def active(self):
        return self.__active

    async def open(self):
        await self.transport.open()
        self.__active = True
        return self

    async def close(self):
        await self.transport.close()
        self.__active = False
        return self

    async def call(self, method, args, kwargs, one_way=False):
        """Calls the requested method and returns the result.

        If an error occured, an :py:class:`~tinyrpc.exc.RPCError` instance
        is raised.

        :param method: Name of the method to call.
        :param args: Arguments to pass to the method.
        :param kwargs: Keyword arguments to pass to the method.
        :param one_way: Whether or not a reply is desired.
        """

        if not self.__active:
            raise RuntimeError('Client is closed')

        req = self.protocol.create_request(method, args, kwargs, one_way)
        req_data = self.serializer.serialize(req.to_data())

        # sends ...
        reply = await self.transport.send_message(req_data, not one_way)

        if one_way:
            # ... and be done
            return

        # ... or process the reply
        rep_data = self.serializer.deserialize(reply)
        rep = self.protocol.parse_response(rep_data)

        if isinstance(rep, ErrorResponse):
            raise rep.to_exception()

        return rep.result

    def get_proxy(self, prefix='', one_way=False):
        """Convenience method for creating a proxy.

        :param prefix: Passed on to :py:class:`~tinyrpc.client.RPCProxy`.
        :param one_way: Passed on to :py:class:`~tinyrpc.client.RPCProxy`.
        :return: :py:class:`~tinyrpc.client.RPCProxy` instance."""
        return Proxy(self, prefix, one_way)

