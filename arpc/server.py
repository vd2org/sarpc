#!/usr/bin/env python
# -*- coding: utf-8 -*-

# FIXME: needs unittests
# FIXME: needs checks for out-of-order, concurrency, etc as attributes
from .exc import RPCError


class RPCServer(object):
    """High level RPC server.

    :param transport: The :py:class:`~tinyrpc.transports.RPCTransport` to use.
    :param protocol: The :py:class:`~tinyrpc.RPCProtocol` to use.
    :param dispatcher: The :py:class:`~tinyrpc.dispatch.RPCDispatcher` to use.
    """

    trace = None
    """Trace incoming and outgoing messages.

    When this attribute is set to a callable this callable will be called directly
    after a message has been received and immediately after a reply is sent.
    The callable should accept three positional parameters:
    * *direction*: string, either '-->' for incoming or '<--' for outgoing data.
    * *context*: the context returned by :py:meth:`~tinyrpc.transport.RPCTransport.receive_message`.
    * *message*: the message string itself.

    Example::

        def my_trace(direction, context, message):
            logger.debug('%s%s', direction, message)

        server = RPCServer(transport, protocol, dispatcher)
        server.trace = my_trace
        server.serve_forever

    will log all incoming and outgoing traffic of the RPC service.
    """

    def __init__(self, protocol, transport, dispatcher, assistant=None):
        self.transport = transport
        self.protocol = protocol
        self.dispatcher = dispatcher
        self.assistant = assistant
        self.trace = None

    async def start(self):
        await self.transport.start(self.handler)

    async def stop(self):
        await self.transport.stop()

    async def handler(self, message):
        """Handle a single request.

        Polls the transport for a new message.

        After a new message has arrived :py:meth:`_spawn` is called with a handler
        function and arguments to handle the request.

        The handler function will try to decode the message using the supplied
        protocol, if that fails, an error response will be sent. After decoding
        the message, the dispatcher will be asked to handle the resultung
        request and the return value (either an error or a result) will be sent
        back to the client using the transport.
        """

        if callable(self.trace):
            self.trace('-->', message)

        try:
            request = self.protocol.parse_request(message)

            if self.assistant:
                await self.assistant.server_check_request(self.protocol, request)

            response = await self.dispatcher.dispatch(request)

        except RPCError as e:
            response = e.error_respond()

        # send reply
        if response is not None:
            if self.assistant:
                await self.assistant.server_sign_response(response)

            result = response.serialize()
            if callable(self.trace):
                self.trace('<--', result)

            return result
