# -*- coding: utf-8 -*-
from __future__ import absolute_import
import demo_common
demo_common.setup()



def main():
    import thrift
    from thrift.protocol import TBinaryProtocol

    import zmq
    from zerothrift import TZmqTransport
    from accounts.account_api import PingService


    endpoint = "tcp://localhost:5555"
    socktype = zmq.REQ

    transport = TZmqTransport(endpoint, socktype)
    protocol = thrift.protocol.TBinaryProtocol.TBinaryProtocol(transport)

    client = PingService.Client(protocol)
    transport.open()

    print client.ping()

if __name__ == "__main__":
    main()