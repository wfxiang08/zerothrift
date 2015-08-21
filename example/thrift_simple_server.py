# -*- coding: utf-8 -*-
from __future__ import absolute_import
import demo_common
demo_common.setup()



from account_service.AccountService import Iface
from account_service.ttypes import UserInfo


# 采用thrift + gevent对外提供服务
# 参考: https://github.com/eleme/gunicorn_thrift
#
from zerothrift import (Server)

# 服务的实现
class AccountProcessor(Iface):
    def get_user_by_id(self, id):
        user_info = UserInfo(id, "hello_%s" % id)
        print "user_name: ", user_info.username
        return user_info

def main():
    # 使用静态的代码，看起来脏一点，但是类型限定更加直接
    from account_service.AccountService import Processor
    processor = Processor(AccountProcessor())

    s = Server(processor, pool_size=5, mode_ppworker=False, profile=True)
    s.bind("tcp://192.168.0.243:10004")
    s.run()

if __name__ == "__main__":
    main()



