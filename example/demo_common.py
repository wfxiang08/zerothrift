# -*- coding: utf-8 -*-
import os
import sys

def setup():
    # 直接引用当前项目的代码
    ROOT = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
    if not ROOT in sys.path[:1]:
        sys.path.insert(0, ROOT)
