# -*- coding: utf-8 -*-
from __future__ import absolute_import
import demo_common
demo_common.setup()


# 采用thrift + gevent对外提供服务
# 参考: https://github.com/eleme/gunicorn_thrift
#
from zerothrift import Server

# 服务的实现
class PingPongDispatcher(object):
    index = 0
    def ping(self):
        self.index += 1
        print "Index: ", self.index
        # sleep(0.1)
        return "pong"

    def progress(self, num1):
        # sleep(0.001)
        # print "Num: ", num1
        return num1

def main():
    # 使用静态的代码，看起来脏一点，但是类型限定更加直接
    from accounts.account_api.PingService import Processor
    processor = Processor(PingPongDispatcher())

    s = Server(processor, pool_size=10)
    s.bind("tcp://127.0.0.1:5556")
    s.run()

if __name__ == "__main__":
    main()



