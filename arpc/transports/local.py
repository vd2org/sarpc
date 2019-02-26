#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging
import typing


from ..transport import ServerTransport, ClientTransport

logger = logging.getLogger('arpc.transports.local')


class LocalServerTransport(ServerTransport):
    """Local Server transport. Useful for experiments and testing."""

    def __init__(self, *, loop=None):
        super().__init__()

        self.__handler = None

    async def process(self, message: bytes):
        print('SERVER RECV:', message)
        if not self.__active:
            raise TransportNotActive

        r = await self.__handler(message)
        print('SERVER SEND:', r)
        return r

    async def start(self, handler: typing.Callable):
        self.__handler = handler
        self.__active = True

    async def stop(self):
        self.__active = False
        self.__handler = None
        logger.info("Closed.")


class LocalClientTransport(ClientTransport):
    """Local Client transport. Useful for experiments and testing."""
    def __init__(self, *, on_send: typing.Callable, loop=None):
        super().__init__()
        self.loop = loop if loop else asyncio.get_event_loop()

        self.__on_send = on_send

    async def open(self):
        self.__active = True

    async def close(self):
        self.__active = False

    async def send_message(self, message, expect_reply=True):
        print('CLIENT SEND:', message)
        r = await self.__on_send(message)
        print('CLIENT RECV:', r)
        return r

