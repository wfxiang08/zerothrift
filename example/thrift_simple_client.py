# -*- coding: utf-8 -*-
from __future__ import absolute_import
from thrift.protocol.TBinaryProtocol import TBinaryProtocol
import demo_common
demo_common.setup()



def main():


    import zmq
    from zerothrift import TZmqTransport
    from accounts.account_api import PingService


    endpoint = "tcp://localhost:5556"
    socktype = zmq.DEALER

    transport = TZmqTransport(endpoint, socktype)
    protocol = TBinaryProtocol(transport)

    client = PingService.Client(protocol)
    transport.open()

    print client.ping()

if __name__ == "__main__":
    main()