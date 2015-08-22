# -*- coding: utf-8 -*-
from __future__ import  absolute_import
import logging
from logging import getLogger
import os
import time

import gevent.pool
import gevent.queue
import gevent.event
import gevent.local
import gevent.lock
import signal
from thrift.Thrift import TProcessor
from thrift.protocol.TBinaryProtocol import (TBinaryProtocol, TBinaryProtocolFactory)
from thrift.transport.TTransport import TMemoryBuffer
import zmq

from zerothrift import (Events, HEARTBEAT_LIVENESS, INTERVAL_INIT, INTERVAL_MAX, HEARTBEAT_INTERVAL, PPP_HEARTBEAT,
                        PPP_STOP, PPP_READY)
from zerothrift.context import Context


logger = getLogger(__name__)


from colorama import init
init()
from colorama import Fore

class TUtf8BinaryProtocol(TBinaryProtocol):
    """
        只要控制数据的输出端，在整个transport上的数据都应该是标准的
    """
    def writeString(self, str):
        if isinstance(str, unicode):
            str = str.encode("utf-8")

        TBinaryProtocol.writeString(self, str)

class TUtf8StrBinaryProtocolFactory(TBinaryProtocolFactory):
    def getProtocol(self, trans):
        prot = TUtf8BinaryProtocol(trans, self.strictRead, self.strictWrite)
        return prot


class Server(object):

    def __init__(self, processor, zmq_socket_type=zmq.DEALER, context=None, pool_size=5, mode_ppworker=False, service=None, profile=False):
        # 1. 获取zeromq context, 以及 events
        self.context = context or Context.get_instance()
        self.events = Events(zmq_socket_type, self.context, mode_ppworker=mode_ppworker, service=service)

        # 2. 设置: mode_ppworker
        if self.events.mode_ppworker:
            self.liveness = HEARTBEAT_LIVENESS
            self.interval = INTERVAL_INIT
            self.heartbeat_at = time.time() + HEARTBEAT_INTERVAL


        self.processor = processor # thrift processor

        self.proto_factory_input = TBinaryProtocolFactory()
        self.proto_factory_output = TUtf8StrBinaryProtocolFactory()


        # 4. gevent
        self.task_pool = gevent.pool.Pool(size=pool_size)

        self.acceptor_task = None


        self.events.create_worker_socket()
        self.endpoint = None

        # 5. 程序退出控制
        self.alive = True
        self.t = 0
        self.count = 0

        self.profile = profile

    def get_heartbeat_msg(self):
        # 协议: byte0(动作) + byte1(版本) + byte2(并发度)
        # 启动时发一个消息，之后间隔一段时间发送一个消息
        #
        return PPP_HEARTBEAT + chr(0) + chr(self.task_pool.free_count())

    def get_ready_msg(self):
        # 协议: byte0(动作) + byte1(版本) + byte2(并发度)
        # 启动时发一个消息，之后间隔一段时间发送一个消息
        #
        return PPP_READY + chr(0) + chr(self.task_pool.free_count())

    # 通过_events来connect, bind服务
    def connect(self, endpoint, resolve=True):
        self.endpoint = endpoint
        return self.events.connect(endpoint, resolve)

    def bind(self, endpoint, resolve=True):
        self.endpoint = endpoint
        return self.events.bind(endpoint, resolve)


    def close(self):
        self.events.close()
        self.stop()


    def handle_request(self, event):

        # t = time.time()
        # 0.2ms
        # 1. 将zeromq的消息转换成为 thrift的 protocols
        trans_input = TMemoryBuffer(event.msg)
        trans_output = TMemoryBuffer()

        proto_input = self.proto_factory_input.getProtocol(trans_input)
        proto_output = self.proto_factory_output.getProtocol(trans_output)

        # 2. 交给processor来处理
        try:
            self.processor.process(proto_input, proto_output)
            # 3. 将thirft的结果转换成为 zeromq 格式的数据
            msg = trans_output.getvalue()
            # print "Return Msg: ", msg, event.id
            if self.profile:
                event.id.extend(["", "%.4f" % time.time()])
                self.events.emit(msg, event.id)
            else:
                self.events.emit(msg, event.id)
        except Exception as e:
            # 如何出现了异常该如何处理呢
            # 程序不能挂
            logging.exception("Exception: %s", e)
            # 如何返回呢?




    def _acceptor(self):
        # run
        #    ---> _acceptor
        #                   ---> _handle_request
        #
        #
        # server的工作模式:
        #   1. Demo服务器可以简单地启动一个ZeroRpcServer, 然后也不用考虑网络 io的一点点时间开销
        #   2. 线上服务器, ZeroRpcServer之前添加了一个queue或load balance, 因此网络io的时间也可以忽略
        #
        last_queue_time = time.time()
        last_event_time = time.time()
        start = True
        while True:
            if self.events.mode_ppworker:

                # 注意: events现在只从 input获取信息, 如果 handle_request 因为什么原因，导致数据没有返回，而代码却堵在这里了。
                # poll_event的参数最小为1，否则就成为0, 则无限等待; 也不能设置为None
                t = time.time()
                event = self.events.poll_event(100) # 1ms(为什么呢?)

                # print "wait time: %.5fms" % ((time.time() - t) * 1000,)


                now = time.time()
                if event:
                    last_queue_time = now
                    last_event_time = now

                    if self.liveness == 0 or start:
                        start = False
                        print Fore.GREEN, "Queue back to life", Fore.RESET

                    # print "Event: ", event
                    if len(event.msg) == 1 and event.msg == PPP_HEARTBEAT:
                        self.liveness = HEARTBEAT_LIVENESS
                    else:
                        # 正常的RPC数据
                        self.liveness = HEARTBEAT_LIVENESS
                        self.task_pool.spawn(self.handle_request, event)

                    self.interval = INTERVAL_INIT
                else:
                    # timeout(太长时间没有回应)
                    if self.alive and (now - last_queue_time >= HEARTBEAT_INTERVAL):
                        last_queue_time = time.time()
                        now = time.time()

                        self.liveness -= 1
                        if self.liveness == 0:
                            print Fore.RED, "ID: ", self.events.identity, "Queue died, Begin to sleep for: ", self.interval, Fore.RESET
                            # 反正都没啥事了，等待就等待

                            gevent.sleep(self.interval)

                            if self.interval < INTERVAL_MAX:
                                self.interval *= 2

                            self.liveness = HEARTBEAT_LIVENESS
                            start = True

                            # 重新注册(恢复正常状态)
                            assert self.endpoint
                            print Fore.RED, "ID: ", self.events.identity, "Reconnection Queue", Fore.RESET
                            self.events.reconnect(self.get_ready_msg())


                # 如果要死了，并且1s内没有新的任务, 并且task_pool为空，则自杀
                if not self.alive and (now - last_event_time) > 1.0 and self.task_pool.free_count() == self.task_pool.size:
                    print Fore.CYAN, "<<<< Suicide Worker Gracefully", Fore.RESET
                    break

                # 自己也需要发送消息给queue(自己活着的时候才发送hb)
                elif now >= self.heartbeat_at and self.alive:
                    print "Send Hb Msg...", self.events.identity
                    self.events.emit(self.get_heartbeat_msg(), None)
                    self.heartbeat_at = time.time() + HEARTBEAT_INTERVAL

                if not self.alive:
                    self.events.emit(PPP_STOP, None)


            else:
                event = self.events.poll_event(1)
                if event:
                    self.task_pool.spawn(self.handle_request, event)

                if not self.alive:
                    break

    def run(self):
        import gevent.monkey
        gevent.monkey.patch_socket()

        # 0. 注册信号(控制运维)
        self.init_signal()

        # 1 ppworker在启动的时候，会告知 lb, 我准备好了，以及支持的并发度
        if self.events.mode_ppworker:
            print "Send Hb Msg..."
            self.events.emit(self.get_ready_msg(), None)

        # 2. 监听数据
        self.acceptor_task = gevent.spawn(self._acceptor)

        # 3. 等待结束
        try:
            self.acceptor_task.get()
        finally:
            self.stop()
            self.task_pool.join(raise_error=True)

    def stop(self):
        if self.acceptor_task is not None:
            self.acceptor_task.kill()
            self.acceptor_task = None

    def init_signal(self):
        def handle_int(*_):
            self.alive = False

        def handle_term(*_):
            # 主动退出
            self.alive = False
        # 2/15
        signal.signal(signal.SIGINT, handle_int)
        signal.signal(signal.SIGTERM, handle_term)



        print Fore.RED, "To graceful stop current worker plz. use:", Fore.RESET
        print Fore.GREEN, ("kill -15 %s" % os.getpid()), Fore.RESET

