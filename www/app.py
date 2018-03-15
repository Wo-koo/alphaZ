#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'zhangzhen'

'''
async web app
'''

import logging

logging.basicConfig(level=logging.INFO)

import asyncio
import os
import json
import time
from datetime import datetime

from aiohttp import web


def index(request_):
    # 这里要写上headers，否则会当作二进制文件下载
    return web.Response(body=b'<h1>Awesome<h1>', headers={'content-type':'text/html'})


async def init(loop_):
    app = web.Application(loop=loop_)
    app.router.add_route('GET', '/', index)
    srv = await loop_.create_server(app.make_handler(), '127.0.0.1', 9000)
    logging.info('server start at http://127.0.0.1:9000.....')
    return srv


loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
