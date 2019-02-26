#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging

from nats.aio.client import Client as NATS

from . import ServerTransport, ClientTransport

logger = logging.getLogger('arpc.transports.nats')

DEFAULT_TIMEOUT = 10
DEFAULT_SERVERS = ("nats://127.0.0.1:4222",)


class NATSServerTransport(ServerTransport):
    """Server transport based on a NATS messaging service."""

    def __init__(self, topic, queue='', servers=None, nats=None, async_mode=True, loop=None):
        self.topic = topic
        self.queue = queue
        self.async_mode = async_mode
        self.loop = loop if loop else asyncio.get_event_loop()
        self.closed = True

        if nats and servers:
            raise RuntimeError("Exactly one of `servers` or `nats` must be specified.")

        self.nats = nats
        self.implicit_nats = nats is not None
        self.subscription = None
        self.servers = servers if servers else DEFAULT_SERVERS

    async def start(self, handler):
        async def _handler(message):
            reply = await handler(message.data)
            if reply:
                await self.nats.publish(message.reply, reply)

        if not self.implicit_nats:
            self.nats = NATS()
            await self.nats.connect(servers=self.servers, io_loop=self.loop)

        logger.info("Listening on topic %s with group %s.", self.topic, self.queue)
        self.subscription = await self.nats.subscribe(self.topic, self.queue, cb=_handler, is_async=self.async_mode)

    async def stop(self):
        if self.closed:
            return

        await self.nats.unsubscribe(self.subscription)
        self.subscription = None
        if self.nats and not self.implicit_nats:
            logger.info("Closing server...")
            await self.nats.close()
            self.nats = None
        self.closed = True
        logger.info("Closed.")


class NATSClientTransport(ClientTransport):
    """Client transport based on a NATS messaging service."""

    def __init__(self, topic, servers=None, nats=None, timeout=DEFAULT_TIMEOUT, loop=None):
        self.topic = topic
        self.timeout = timeout
        self.loop = loop if loop else asyncio.get_event_loop()
        self.closed = True

        if nats and servers:
            raise RuntimeError("Exactly one of `servers` or `nats` must be specified.")

        self.nats = nats
        self.implicit_nats = nats is not None
        self.servers = servers if servers else DEFAULT_SERVERS

    async def open(self):
        if not self.implicit_nats:
            self.nats = NATS()
            await self.nats.connect(servers=self.servers, io_loop=self.loop)
        self.closed = False

    async def close(self):
        if self.nats and not self.implicit_nats:
            await self.nats.close()
            self.nats = None
        self.closed = True

    async def send_message(self, message, expect_reply=True):
        if self.closed:
            raise RuntimeError('Transport is closed')

        if expect_reply:
            reply = await self.nats.timed_request(self.topic, message, self.timeout)
            return reply.data
        else:
            await self.nats.publish(self.topic, message)

    def __del__(self):
        if not self.closed:
            logger.warning("Unclosed client transport!")
