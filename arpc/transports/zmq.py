#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging
import typing

import zmq
import zmq.asyncio
import zmq.devices

from . import ServerTransport, ClientTransport

logger = logging.getLogger('arpc.transports.zmq')

DEFAULT_PARALLEL_TASKS = 3


class ZmqServerTransport(ServerTransport):
    """Server transport based on a ZeroMQ req/rep socket."""

    def __init__(self, bind_url: str, topic: typing.Optional[bytes] = None, context: zmq.Context = None,
                 parallel_tasks: int = DEFAULT_PARALLEL_TASKS, loop=None):
        self.topic = topic
        self.bind_url = bind_url
        self.context = context
        self.parallel_tasks = parallel_tasks
        self.loop = loop if loop else asyncio.get_event_loop()
        self.closed = True

        self.implicit_context = context is not None

        self._awaits = list()

    async def start(self, handler):
        async def _handler(message):
            reply = await handler(message.data)
            if reply:
                await self.nats.publish(message.reply, reply)

        async def _srv():
            sock = self._ctx.socket(zmq.REP)
            sock.connect("inproc://broker_%s" % id(self))
            while True:
                reply = None
                try:
                    message = await sock.recv_pyobj()
                    reply = await handler(message)
                finally:
                    await sock.send_pyobj(reply)

        frontend = self.context.socket(zmq.ROUTER)
        backend = self.context.socket(zmq.DEALER)

        frontend.bind(self.bind_url)
        backend.bind("inproc://broker_%s" % id(self))

        zmq.proxy(frontend, backend)

        for i in range(self.parallel_tasks):
            self._awaits.append(_srv())

        asyncio.gather(*self._awaits, loop=self.loop)

        self.closed = False

    async def stop(self):
        self.closed = True
        logger.info("Closed.")


class ZmqClientTransport(ClientTransport):
    """Client transport based on a :py:const:`zmq.REQ` socket.

    :param socket: A :py:const:`zmq.REQ` socket instance, connected to the
                   server socket.
    """

    def __init__(self, socket):
        self.socket = socket

    async def send_message(self, message, expect_reply=True):
        if six.PY3 and isinstance(message, six.string_types):
            # pyzmq won't accept unicode strings
            message = message.encode()

        await self.socket.send(message)

        if expect_reply:
            return await self.socket.recv()

    @classmethod
    def create(cls, zmq_context, endpoint):
        """Create new client transport.

        Instead of creating the socket yourself, you can call this function and
        merely pass the :py:class:`zmq.core.context.Context` instance.

        :param zmq_context: A 0mq context.
        :param endpoint: The endpoint the server is bound to.
        """
        socket = zmq_context.socket(zmq.REQ)
        socket.connect(endpoint)
        return cls(socket)
