# -*- coding: utf-8 -*-
from __future__ import absolute_import
import time
import demo_common


demo_common.setup()


def main():

    from accounts.account_api.PingService import Client as PingClient
    from zerothrift import (TimeoutException, get_transport, get_protocol)


    endpoint = "tcp://localhost:5550"
    service = "account"

    # 如何管理zeromq的client呢?
    # 如何有效管理 transport呢?
    transport = get_transport(endpoint)
    protocol = get_protocol(service)
    client = PingClient(protocol)


    total_times = 10000
    t1 = time.time()
    result_set = set()
    for i  in range(0, total_times):
        print "index: ", i
        # time.sleep(0.1)
        try:
            result = client.progress(i)
            result_set.add(result)
        except TimeoutException as e:
            print "TimeoutException: ", e
        except Exception as e:
            print "Exception: ", e

        if i % 200 == 0:
            print "QPS: %.2f" % (i / (time.time() - t1), )

    print "Total Result: ", len(result_set)
    t = time.time() - t1
    print "Elapsed: ",  t / total_times
if __name__ == "__main__":
    main()