class ServerTransport:
    """Base class for all server transports."""

    def __init__(self):
        self.__active = False

    @property
    def active(self):
        return self.__active

    async def start(self, handler):
        """Receive a message from the transport.

        Blocks until another message has been received. May return a context
        opaque to clients that should be passed on
        :py:func:`~tinyrpc.transport.ServerTransport.send_reply` to identify
        the client later on.

        :return: A tuple consisting of ``(context, message)``.
        """
        raise NotImplementedError()

    async def stop(self):
        """Sends a reply to a client.

        The client is usually identified by passing ``context`` as returned
        from the original
        :py:func:`~tinyrpc.transport.Transport.receive_message` call.

        Messages must be strings, it is up to the sender to convert the
        beforehand. A non-string value raises a :py:exc:`TypeError`.

        :param context: A context returned by
                        :py:func:`~tinyrpc.transport.ServerTransport.receive_message`.
        :param reply: A string to send back as the reply.
        """
        raise NotImplementedError


class ClientTransport:
    """Base class for all client transports."""

    def __init__(self):
        self.__active = False

    @property
    def active(self):
        return self.__active

    async def open(self):
        raise NotImplementedError

    async def close(self):
        raise NotImplementedError

    async def send_message(self, message, expect_reply=True):
        """Send a message to the server and possibly receive a reply.

        Sends a message to the connected server.

        Messages must be strings, it is up to the sender to convert the
        beforehand. A non-string value raises a :py:exc:`TypeError`.

        This function will block until one reply has been received.

        :param message: A string to send.
        :return: A string containing the server reply.
        """
        raise NotImplementedError()
