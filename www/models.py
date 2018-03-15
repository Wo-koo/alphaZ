#!/usr/bin/env python3
# -*- coding: utf-8 -*-


__author__ = 'zhangzhen'

'''
Models for usr
'''

from www.orm import StringField, Model, BooleanField, FloatField
import uuid
import time


def next_id():
    """
    当主键缺省时，返回值作为主键
    :return:
    """
    # uuid的作用是生成唯一标识符，该标识符不需要有具体意义
    return '%015d%s000' % (int(time.time()* 1000),uuid.uuid4().hex)

# 这里我们先做一个简单的用户model，用于注册和登陆
class User(Model):
    __table__ = 'users'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    passwd = StringField(ddl='varchar(50)')
    admin = BooleanField()
    name = StringField(ddl='varchar(50)')
    # 时间变量我们用float来存储，这样方便排序和类型转换
    created_at = FloatField(default=time.time)