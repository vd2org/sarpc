#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .protocols import Protocol
from .transports import ClientTransport


class Client:
    """Client for making RPC calls to connected servers.

    :param protocol: An :py:class:`~tinyrpc.RPCProtocol` instance.
    :param transport: A :py:class:`~tinyrpc.transports.ClientTransport`
                      instance.
    """

    def __init__(self, protocol: Protocol, transport: ClientTransport):
        self.protocol = protocol
        self.transport = transport
        self.closed = True

    async def open(self):
        await self.transport.open()
        self.closed = False
        return self

    async def close(self):
        await self.transport.close()
        self.closed = True
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

        if self.closed:
            raise RuntimeError('Client is closed')

        req = self.protocol.create_request(method, args, kwargs, one_way)

        # sends ...
        reply = await self.transport.send_message(req.serialize(), not one_way)

        if one_way:
            # ... and be done
            return

        # ... or process the reply
        rep = self.protocol.parse_response(reply)

        if isinstance(rep, self.protocol.ErrorResponse):
            raise rep.to_exception()

        return rep.result

    def get_proxy(self, prefix='', one_way=False):
        """Convenience method for creating a proxy.

        :param prefix: Passed on to :py:class:`~tinyrpc.client.RPCProxy`.
        :param one_way: Passed on to :py:class:`~tinyrpc.client.RPCProxy`.
        :return: :py:class:`~tinyrpc.client.RPCProxy` instance."""
        return Proxy(self, prefix, one_way)


class Proxy:
    """Create a new remote proxy object.

    Proxies allow calling of methods through a simpler interface. See the
    documentation for an example.

    :param client: An :py:class:`~tinyrpc.client.RPCClient` instance.
    :param prefix: Prefix to prepend to every method name.
    :param one_way: Passed to every call of
                    :py:func:`~tinyrpc.client.call`.
    """

    def __init__(self, client, prefix='', one_way=False):
        self.client = client
        self.prefix = prefix
        self.one_way = one_way

    def __getattr__(self, name):
        """Returns a proxy function that, when called, will call a function
        name ``name`` on the client associated with the proxy.
        """
        return lambda *args, **kwargs: self.client.call(
            self.prefix + name,
            args,
            kwargs,
            one_way=self.one_way
        )
