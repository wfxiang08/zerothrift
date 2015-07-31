# ZeroThrift
* 基本原理同zerorpc
* python版的RPC的Client&Server, 和rpc_proxy: https://github.com/wfxiang08/rpc_proxy/blob/master/README.md 配合使用

## 数据序列化采用thrift
* 和zerorpc相比，将序列化协议改为thrift
 * msgpack: 简单灵活，但是过度的自由可能是一个灾难
 * thrift：数据有类型，可以规范客户端的调用(从工程角度更加合适)

## ZeroThrift RPC

### 工作模式1
* 简单的zeromq DEALER + ROUTER模式

```bash
cd example
# 在一个Shell中启动
python thrift_simple_server.py
# 在另外一个Shell中启动
python thrift_simple_client.py
```

* Client端的代码

```python
from account_service.AccountService import Client
from zerothrift import (TimeoutException, get_transport, get_protocol)

# 创建transport
_ = get_transport("tcp://127.0.0.1:10004", timeout=5)

# 创建client
protocol = get_protocol("")
client = Client(protocol)


# 调用client的方法
result = client.get_user_by_id(i)

```
* Server端的代码

```python
from account_service.AccountService import Processor
# 创建Processor
processor = Processor(AccountProcessor())

# 创建Server
s = Server(processor, pool_size=5, mode_ppworker=False)
s.bind("tcp://127.0.0.1:10004")
s.run()
```


### 工作模式2
* DEALER + (ROUTER, DEALER) + (ROUTER, ROUTER) + DEALER(4层结构)
* 中间两个环节采用Go实现，见: https://github.com/wfxiang08/rpc_proxy

```bash
# 需要在本地启动一个zk
rpc_proxy -c config.ini
rpc_lb -c config.ini
python thrift_pp_worker.py
python thrift_proxy_client.py
```
* Client端的代码

```python
_ = get_transport(endpoint)
protocol = get_protocol(service) # 和工作模式1的差别在与service不为空
client = Client(protocol)
```

* Server端代码

```python
# 和工作模式1区别在于: mode_ppworker 为True, 它会和rpc_lb进行心跳，数据通信
s = Server(processor, pool_size=worker_pool_size, service=service, mode_ppworker=True)
s.connect(endpoint)
s.run()
```

