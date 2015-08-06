# -*- coding: utf-8 -*-

from __future__ import absolute_import
from zerothrift.context import *
from zerothrift.events import *
from zerothrift.core.client import *
from zerothrift.core.server import *

_transport = None
_endpoint = None
_context = None


def get_transport(endpoint=None, timeout=5):
    """
    在Django等单线程模型中，可以直接使用 get_transport；这里假定所有的endpoint是一样的
    :param endpoint:
    :param timeout:
    :return:
    """
    global _transport, _endpoint, _context

    assert _endpoint is None or _endpoint == endpoint

    if not _context:
        _context = Context.get_instance()

    if not _transport:
        _endpoint = endpoint
        _transport = TZmqTransport(endpoint, zmq.DEALER, ctx=_context, timeout=timeout)
        _transport.open()
    return _transport

def create_transport(endpoint=None, timeout=5):
    """
    创建一个transport, 这个可以创建到不同的endpoint的transport, 或者为一个pool创建多个transport
    :param endpoint:
    :param timeout:
    :return:
    """
    global _context
    if not _context:
        _context = Context.get_instance()

    transport = TZmqTransport(endpoint, zmq.DEALER, ctx=_context, timeout=timeout)
    transport.open()
    return transport



def get_protocol(service, transport=None):
    assert _transport
    return TZmqBinaryProtocol(transport or _transport, service=service)



# 配置文件相关的参数
RPC_DEFAULT_CONFIG = "config.ini"

RPC_ZK = "zk"
RPC_ZK_TIMEOUT = "zk_session_timeout"

RPC_PRODUCT = "product"
RPC_SERVICE = "service"

RPC_FRONT_HOST = "front_host"
RPC_FRONT_PORT = "front_port"
RPC_IP_PREFIX = "ip_prefix"

RPC_BACK_ADDRESS = "back_address"

RPC_WORKER_POOL_SIZE = "worker_pool_size"
RPC_PROXY_ADDRESS  = "proxy_address"


def parse_config(config_path):
    config = {}
    for line in open(config_path, "r").readlines():
        line = line.strip()
        if not line or line.find("#") != -1:
            continue
        items = line.split("=")
        if len(items) >= 2:
            config[items[0]] = items[1]
    return config

