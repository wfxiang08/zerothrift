# -*- coding: utf-8 -*-

from __future__ import absolute_import
import os
from random import randint
import gevent

import zmq.green as gzmq
from gevent import select

import zerothrift.gevent_zmq as zmq


PPP_READY = "\x01"      # 数据READY
PPP_HEARTBEAT = "\x02"  # 心跳信号
PPP_STOP = "\x03"       # 停止心跳

HEARTBEAT_LIVENESS = 5
HEARTBEAT_INTERVAL = 1 # 1s
INTERVAL_INIT = 1
INTERVAL_MAX = 4

EMPTY_STRING = b''

class Events(object):
    """
        Events内部管理: zmq.Socket
    """

    def __init__(self, zmq_socket_type, context, mode_ppworker = False, service = ""):

        self.context = context
        self.zmq_socket_type = zmq_socket_type


        assert self.context

        # 当前的Server是否以 ppworker的模式运行，默认为False
        self.mode_ppworker = mode_ppworker
        self.service = service

        self.identity = "%s-%04X-%04X" % (service or "test", os.getpid(), randint(0, 0x10000))

        self.socket = None
        self.poller = gzmq.Poller()

        self.endpoint = None
        self.create_worker_socket()


    def create_worker_socket(self):
        """
        创建一个新的连接，并且
        :return:
        """
        self.socket = zmq.Socket(self.context, self.zmq_socket_type)
        self.socket.setsockopt(zmq.IDENTITY, self.identity)


        self.poller.register(self.socket, zmq.POLLIN)

        # zeromq send是异步的，因此也不要考虑优化这一块的性能
        self._send = self.socket.send_multipart
        self._recv = self.socket.recv_multipart

    def reconnect(self, READY_MSGS):
        """
        当前的worker重新连接到queue上
        :return:
        """
        assert self.mode_ppworker

        print "Reconnection to queue: "

        # 关闭之前的连接
        if self.socket:
            self.poller.unregister(self.socket)
            self.socket.setsockopt(zmq.LINGER, 1) # 旧的数据继续发送
            self.socket.close()
            self.socket = None

        self.create_worker_socket()

        endpoint = self.endpoint
        self.endpoint = None
        self.connect(endpoint)

        # 作为一个DEALER，告知load balance
        self.emit(READY_MSGS, None)

    def poll_event(self, timeout):
        """
        检查是否有来自socket的数据, 如果有返回event, 如果没有返回None
        :return:
        """
        socks = dict(self.poller.poll(timeout))
        if socks.get(self.socket) == zmq.POLLIN:
            return self.recv()
        else:
            return None


    @property
    def recv_is_available(self):
        """
            默认情况下: _zmq_socket_type为 zmq.ROUTER
        :return:
        """
        return self.zmq_socket_type in (zmq.PULL, zmq.SUB, zmq.DEALER, zmq.ROUTER)

    def __del__(self):
        try:
            if self.socket and not self.socket.closed:
                self.close()
        except AttributeError:
            pass
        except TypeError:
            pass

    def close(self):
        self.socket.close()

    def _resolve_endpoint(self, endpoint, resolve=True):
        # 对: endpoint调用一些事先准备好的func, 进行处理; 默认不做任何事情
        if isinstance(endpoint, (tuple, list)):
            r = []
            for sub_endpoint in endpoint:
                r.extend(self._resolve_endpoint(sub_endpoint, resolve))
            return r
        return [endpoint]

    def connect(self, endpoint, resolve=True):
        assert not self.endpoint
        self.endpoint = endpoint

        r = []
        for endpoint_ in self._resolve_endpoint(endpoint, resolve):
            r.append(self.socket.connect(endpoint_))
        return r

    def bind(self, endpoint, resolve=True):
        """
            将_socket绑定到指定的endpoint
        :param endpoint:
        :param resolve:
        :return:
        """
        assert not self.endpoint
        self.endpoint = endpoint

        r = []
        for endpoint_ in self._resolve_endpoint(endpoint, resolve):
            r.append(self.socket.bind(endpoint_))
        return r

    def create_event(self, msg, id):
        """
            创建一个Event对象
        :param name:
        :param args:
        :param xheader:
        :return:
        """
        event = Event(msg, id)
        return event

    def emit_event(self, event, id=None):
        """
        发送Event
        :param event:
        :param id:
        :return:
        """
        # id的格式
        # 例如:
        # None
        # ["client_id"]
        # ["client_id0", "", "client_id1"]
        # 和Msg的组合:
        # ["client_id", "", msg]
        #
        if id is not None:
            # 带有identity的情况
            parts = list(id)
            parts.extend([EMPTY_STRING, event.msg])

        elif self.zmq_socket_type in (zmq.DEALER, zmq.ROUTER):
            # 都以: REQ为标准，数据统一处理为: ("", data)
            parts = (EMPTY_STRING, event.msg)
        else:
            # 其他的type?
            parts = [event.msg]

        # print "emit_event: ", parts

        self._send(parts)

    def emit(self, msg, id = None):
        assert id is None or isinstance(id, (list, tuple))
        event = self.create_event(msg, id)
        return self.emit_event(event, id)

    def recv(self):
        # 读取用户请求
        parts = self._recv()
        if len(parts) == 1:
            identity = None
            msg = parts[0]
        else:
            identity = parts[0:-2]
            msg = parts[-1]

        # print "parts: ", parts
        event = Event(msg, identity)
        return event

    def setsockopt(self, *args):
        return self.socket.setsockopt(*args)


class Event(object):
    """
        将name, _args, _header进行打包
    """

    __slots__ = ['_msg', '_id']

    def __init__(self, msg, id=None):
        self._msg = msg
        self._id = id


    @property
    def msg(self):
        return self._msg

    @msg.setter
    def msg(self, v):
        self._msg = v

    @property
    def id(self):
        return self._id

    def __str__(self, ignore_args=False):
        if self.msg == PPP_HEARTBEAT:
            return "heartbeat"
        else:
            return "Thrift Event: " + str(self._id or "_id_") + self._msg

def get_stack_info():
    import inspect
    stacks = inspect.stack()
    results = []
    for stack in stacks[2:]:
        func_name = "%s %s %s %d" % (stack[1], stack[3], stack[4], stack[2])
        func_name = func_name.replace("/System/Library/Frameworks/Python.framework/Versions/2.7/lib/python2.7/", "")
        results.append(func_name)
    return "\n".join(results)
