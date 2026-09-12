# -*- coding: utf-8 -*-
"""演示入口：python Main.py [主播抖音号]"""
import sys

import Douyin

if __name__ == "__main__":
    acct = sys.argv[1] if len(sys.argv) > 1 else "J1an9u9u"
    print(Douyin.query_live_status(acct, is_target=True))   # Py 对象输出
    print(Douyin.query_live_status(acct, is_target=False))  # JSON 输出
