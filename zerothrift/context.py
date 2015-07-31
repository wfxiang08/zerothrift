# -*- coding: utf-8 -*-

import gevent_zmq as zmq

class Context(zmq.Context):
    _instance = None

    def __init__(self):
        super(zmq.Context, self).__init__()


    @staticmethod
    def get_instance():
        if Context._instance is None:
            Context._instance = Context()
        return Context._instance

