# -*- coding: utf-8 -*-
from __future__ import  absolute_import
from logging import getLogger
from StringIO import StringIO
import os

from thrift.transport.TTransport import CReadableTransport
from thrift.transport.TTransport import TTransportBase
import zmq

from zerothrift import Events, Context


logger = getLogger(__name__)
from thrift.protocol.TBinaryProtocol import TBinaryProtocol



class TimeoutException(Exception):
    pass

SEQ_NUM_MAX = 9999
SEQ_NUM_HIGH_THRESHOLD = SEQ_NUM_MAX - 1000
SEQ_NUM_LOW_THRESHOLD = 1000
SEQ_NUM_MIN = 1

class TZmqTransport(TTransportBase, CReadableTransport):
    def close(self):
        self._events.close()

    # 通过_events来connect, bind服务
    def connect(self, endpoint, resolve=True):
        return self._events.connect(endpoint, resolve)

    def bind(self, endpoint, resolve=True):
        return self._events.bind(endpoint, resolve)

    def __init__(self, endpoint, sock_type = zmq.DEALER, ctx = None, timeout=5): # zmq.DEALER
        """
        如果采用了 local proxy,
        :param endpoint:
        :param sock_type:
        :param ctx:
        :param service:
        :return:
        """

        self._context = ctx or Context.get_instance()   # 获取zeromq context
        self._events = Events(sock_type, self._context)
        self._events.setsockopt(zmq.IDENTITY, "client-%4d" % os.getpid())

        self._endpoint = endpoint
        self._wbuf = StringIO()
        self._rbuf = StringIO()
        self.service = None
        self.timeout = timeout * 1000 # seconds --> milli-seconds
        self.seqNum = 0

    def open(self):
        self.connect(self._endpoint)

    def read(self, size):
        ret = self._rbuf.read(size)
        if len(ret) != 0:
            return ret

        # buf中的数据处理完毕了，说明一个message应该处理完毕了
        self._read_message()
        return self._rbuf.read(size)

    def get_seq_num(self, event_ids):
        for id in event_ids:
            if id:
                return int(id)
            else:
                continue
        return None

    def _read_message(self):
        # event = self._events.recv()

        event = self._events.poll_event(self.timeout)

        while event:
            # print "EventId: ", event.id
            seqNum = self.get_seq_num(event.id)

            # 可能的情况:
            # seqNum要么 <= self.seqNum, 要么: 远远大于 self.seqNum
            # 接受到的event是之前的event
            if seqNum < self.seqNum or (seqNum > SEQ_NUM_HIGH_THRESHOLD and self.seqNum < SEQ_NUM_LOW_THRESHOLD):
                event = self._events.poll_event(self.timeout)
            else:
                break

        if not event:
            raise TimeoutException()
        else:
            self._rbuf = StringIO(event.msg)

    def write(self, buf):
        self._wbuf.write(buf)

    def flush(self):
        msg = self._wbuf.getvalue()
        self._wbuf = StringIO()

        # 范围: 1 ~ 10000 (防止seqNum过长)
        self.seqNum += 1
        if self.seqNum > SEQ_NUM_MAX:
            self.seqNum = SEQ_NUM_MIN

        # 将Thrift转换成为zeromq
        if self.service:
            # <service, '', msg>
            self._events.emit(msg, [self.service, "", str(self.seqNum)]) # client似乎没有id
        else:
            # <msg>
            self._events.emit(msg, [str(self.seqNum)]) # client似乎没有id

    # Implement the CReadableTransport interface.
    @property
    def cstringio_buf(self):
        return self._rbuf

    # NOTE: This will probably not actually work.
    def cstringio_refill(self, prefix, reqlen):
        while len(prefix) < reqlen:
            self.read_message()
            prefix += self._rbuf.getvalue()
        self._rbuf = StringIO(prefix)
        return self._rbuf


class TZmqBinaryProtocol(TBinaryProtocol):
    """
        主要用户client端的数据的输出
    """
    def __init__(self, trans, strictRead=False, strictWrite=True, service=None):
        TBinaryProtocol.__init__(self, trans, strictRead, strictWrite)
        self.service = service
    def writeString(self, str):
        # 确保所有的str为utf-8
        if isinstance(str, unicode):
            str = str.encode("utf-8")
        TBinaryProtocol.writeString(self, str)

    def writeMessageBegin(self, name, type, seqid):
        assert isinstance(self.trans, TZmqTransport)
        # 在数据输出之前，先设置好: service
        self.trans.service = self.service

        TBinaryProtocol.writeMessageBegin(self, name, type, seqid)