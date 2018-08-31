#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging

import aiohttp.web

from . import ServerTransport, ClientTransport

logger = logging.getLogger('arpc.transports.aiohttp')

DEFAULT_TIMEOUT = 10
DEFAULT_SERVER_PORT = 80


class AioHTTPServerTransport(ServerTransport):
    """Server transport based on a aiohttp."""

    def __init__(self, host=None, port=DEFAULT_SERVER_PORT, loop=None):
        self.loop = loop if loop else asyncio.get_event_loop()
        self.host = host
        self.port = port
        self.server = None

    async def start(self, handler):
        async def _handler(request: aiohttp.web.BaseRequest):
            if request.method != 'POST':
                logger.warning("Bad method from %s.", request.remote)
                return aiohttp.web.Response(status=400)

            body = await request.read()

            response = await handler(body)
            headers = {'Content-Type': 'application/json'}
            return aiohttp.web.Response(body=response, headers=headers)

        logger.info("Listening on http://%s:%s%s", self.host, self.port)

        webserver = aiohttp.web.Server(_handler)
        self.server = await self.loop.create_server(webserver, self.host, self.port, backlog=128)

    async def stop(self):
        if self.server:
            logger.info("Closing server...")
            self.server.close()
            await self.server.wait_closed()
            logger.info("Closed.")


class AioHTTPClientTransport(ClientTransport):
    """Client transport based on a aiohttp."""

    def __init__(self, url, timeout=DEFAULT_TIMEOUT, session=None, loop=None):
        self.url = url
        self.timeout = timeout
        self.loop = loop if loop else asyncio.get_event_loop()
        self.closed = True
        self.session = session
        self.implicit_session = session is not None

    async def open(self):
        if not self.implicit_session:
            self.session = aiohttp.ClientSession(loop=self.loop)
        self.closed = False

    async def close(self):
        if self.session and not self.implicit_session:
            await self.session.close()
            self.session = None
        self.closed = True

    async def send_message(self, message, expect_reply=True):
        if self.closed:
            raise RuntimeError('Transport is closed')

        headers = {'Content-Type': 'application/json'}
        response = await self.session.post(self.url, data=message, headers=headers, timeout=self.timeout)

        if expect_reply:
            return await response.read()

    def __del__(self):
        if not self.closed:
            logger.warning("Unclosed client transport!")
