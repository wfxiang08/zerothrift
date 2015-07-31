# ZeroThrift
* 基本原理同zerorpc

## 数据序列化采用thrift
* 和zerorpc相比，将序列化协议改为thrift
 * msgpack: 简单灵活，但是过度的自由可能是一个灾难
 * thrift：数据有类型，可以规范客户端的调用(从工程角度更加合适)

## ZeroThrift Server

```python
# 工作模式1
# Server
from zerothrift import Server, events

# 定义Thrift的Processor的实现
class PingPongDispatcher(object):
    def ping(self):
        return "pong"

# 创建Thrift Processor
from accounts.account_api.PingService import Processor
processor = Processor(PingPongDispatcher())

# 创建一个Server
s = Server(processor, pool_size=10)
s.bind("tcp://127.0.0.1:5556")
s.run()


# 对应的Client:
import zmq
from zerothrift import TZmqTransport
from accounts.account_api import PingService
endpoint = "tcp://localhost:4242"
socktype = zmq.REQ

transport = TZmqTransport(None, endpoint, socktype)
protocol = thrift.protocol.TBinaryProtocol.TBinaryProtocol(transport)
client = PingService.Client(protocol)
transport.open()

print client.ping()

# 工作模式2:

# Server
from zerothrift import Server, events

# 定义Thrift的Processor的实现
class PingPongDispatcher(object):
    def ping(self):
        return "pong"

# 创建Thrift Processor
from accounts.account_api.PingService import Processor
processor = Processor(PingPongDispatcher())

# 创建一个Server
s = Server(processor, pool_size=10)
s.connect("tcp://127.0.0.1:5556")
s.run()

# 中间增加一个zeromq queue或者普通的load balance

# Client同上

# 工作模式3:
events.mode_ppworker = True
events.service = "demo"
# 开启 Paranoid Pirate queue 模式，如果queue挂了，重启之后RPC Server能自动重连，增加了系统的高可用
s = Server(app, pool_size=10)
s.connect("tcp://127.0.0.1:5556")
s.run()

# queue采用: ppqueue（参考zmq4中的demo)


# 其他的
# TODO：需要充分研究zeromq, 挖掘其强大的功能
```