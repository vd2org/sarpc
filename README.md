# Powerful asyncio rpc library

The arpc is a complex asynchonius framework. It implements an rpc client and an rpc server on top of the up-to-date 
python asyncio framework. 

Comes in with the three following features;
1. A rpc Protocol API
2. Serializator is a serialization/deserialization module
3. protocol data to binary form converter 
4. transport that transfers serialized data from client to server and back.

You can use any combination of protocols, serializarors and transportes or extend the framework with your own
implementations.

Initial code was derived from [tinyrpc](https://tinyrpc.readthedocs.io/en/latest/) but now has been completely rewriten.

Pull requests are welcome. 

## Supported protocols

* [JSONRPC 2.0](https://www.jsonrpc.org/specification)
* pythonrpc

## Supported serializators

* json
* pickle
* msgpack

## Supported transports

* local for inporcess testing
* aiohttp via [aiohttp](https://aiohttp.readthedocs.io/en/stable/)
* nats via [asyncio-nats-client](https://github.com/nats-io/asyncio-nats)
* ZeroMQ via [pyzmq](https://pyzmq.readthedocs.io/en/latest/)

## Requirements

* Python 3.6 or higher

## Optional requirements

* aiohttp for aiohttp transport
* asyncio-nats-client for nats transport
* pyzmq for ZeroMQ transport