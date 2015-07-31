# -*- coding: utf-8 -*-
from __future__ import absolute_import
import time
import demo_common

demo_common.setup()


def main():
    from zerothrift import RPC_DEFAULT_CONFIG, RPC_SERVICE, RPC_PROXY_ADDRESS
    from zerothrift import parse_config
    from account_service.AccountService import Client as PingClient
    from zerothrift import (TimeoutException, get_transport, get_protocol)


    config_path = RPC_DEFAULT_CONFIG
    config = parse_config(config_path)
    endpoint = config[RPC_PROXY_ADDRESS]
    service = config[RPC_SERVICE]

    _ = get_transport(endpoint)
    protocol = get_protocol(service)
    client = PingClient(protocol)


    total_times = 10000
    t1 = time.time()

    for i in range(0, total_times):
        try:
            result = client.get_user_by_id(i)
            print "Index: ", i, ", username: ", result.username
        except TimeoutException as e:
            print "TimeoutException: ", e
        except Exception as e:
            print "Exception: ", e

        if i % 200 == 0:
            print "QPS: %.2f" % (i / (time.time() - t1), )

    t = time.time() - t1
    print "Round Trip: %.4fs" % (t / total_times)

if __name__ == "__main__":
    main()