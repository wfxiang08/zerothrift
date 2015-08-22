# -*- coding: utf-8 -*-
from __future__ import absolute_import
import time

import demo_common



demo_common.setup()



def main():


    from account_service.AccountService import Client
    from zerothrift import (TimeoutException, get_transport, get_protocol)

    _ = get_transport("tcp://127.0.0.1:10004", timeout=5, profile=True)

    protocol = get_protocol("")
    client = Client(protocol)


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

if __name__ == "__main__":
    main()