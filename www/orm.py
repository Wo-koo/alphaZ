#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from exceptions import StandardError
import asyncio,logging
import aiomysql


__author__ = 'zhangzhen'

'''object relationship mapping'''


def log(sql, args=()):
    """
    日志记录
    :param sql: sql语句
    :param args: 参数相关
    :return:
    """
    logging.info('SQL: %s args: %s' % (sql,args))



async def create_pool(loop_, **kw):
    """
    定义连接池函数，避免重复连接耗时
    :param loop_: 连接池
    :param kw: 连接参数
    :return:
    """
    logging.info('create database connection pool.....')
    global __pool
    __pool = await aiomysql.create_pool(
        host=kw.get('host', 'localhost'),
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset', 'utf-8'),
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop = loop_
    )


# 下面的语句将会定义一些常用的类似:select,insert,delete等语句的函数，方便执行

async def select(sql, args, size=None):
    """
    封装的select语句函数
    :param sql: select 的sql语句
    :param args: sql语句中的参数
    :param size: 设定获取数据的大小
    :return:
    """
    log(sql, args)
    global __pool
    async with __pool.get() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql.replace('?', '%s'), args or ())
            if  size:
                rs = await cur.fetchmary(size)
            else:
                rs = await cur.fetchall()
        logging.info('rows returned: %s' % len(rs))
        return rs


async def execute(sql, args, autocommit=True):
    """
    封装insert,update,delete语句，因为其操作相似就封装到一个函数里
    :param sql:
    :param args:
    :param autocommit:
    :return:
    """
    log(sql,args)
    global __pool
    # 获得连接池中的连接
    async with __pool.get() as conn:
        if not autocommit:
            await conn.begin()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql.replace('?', '%s'), args)
                # 返回受影响的行数
                affected = cur.rowcount
            if not autocommit:
                await conn.commit()
        except BaseException as e:
            if not autocommit:
                await conn.rollback()
            log(e)
            raise
        return affected


'''************************************************************'''
def create_args_string(num):
    """
    用来生成一串占位符
    :param num: 占位符的个数
    :return: 一串占位符
    """
    l = []
    for n in range(num):
        l.append('?')
    return ','.join(l)

# 这里的stringField和Field不是很明白起到了什么作用
class Field(object):

    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        # default是为了让ORM可以自己填入缺省值，处理起来特别方便
        self.default = default

    def __str__(self):
        return '<%s, %s, %s>' % (self.__class__.__name__, self.column_type, self.name)

class StringField(Field):

    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)

class BooleanField(Field):

    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)

class FloatField(Field):

    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)

'''***********************************************************************'''
# Model的Mate
class ModelMate(type):

    def __new__(mcs, name, bases, attrs):
        if name == 'Model':
            return type.__new__(mcs, name, bases, attrs)
        table_name = attrs.get('__table__', None) or name
        logging.info('found model: %s (table: %s)' % (name, table_name))
        mappings = dict()
        fields = []
        primary_key = None
        for key, value in attrs.items():
            if isinstance(value, Field):
                logging.info(' found mapping : %s ==> %s' % (key, value))
                mappings[key] = value
                if value.primary_key:
                    # 找到主键
                    if primary_key:
                        raise StandardError('Duplicate primary key for field : %s' % key)
                    primary_key = key
                else:
                    fields.append(key)
        if not primary_key:
            raise StandardError('Primary key not found')
        for key in mappings.keys():
            attrs.pop(key)
        escaped_fields = list(map(lambda f: '%s' % f, fields))
        attrs['__mappings__'] = mappings # 保存属性和列的映射关系
        attrs['__table__'] = table_name
        attrs['__primary_key__'] = primary_key # 主键属性名
        attrs['__fields__'] = fields # 除主键以外的属性名
        attrs['__select__'] = "select '%s', '%s' from '%s'" % (primary_key, ','.join(escaped_fields),table_name)
        attrs['__insert__'] = "insert into '%s' (%s, '%s') values (%s)" % (table_name, ','.join(escaped_fields),primary_key, create_args_string(len(escaped_fields)+1))
        attrs['__update__'] = "update '%s' set %s where '%s'=?" % (table_name, ','.join(map(lambda f: "'%s'=?" % (mappings.get(f).name or f), fields)), primary_key)
        attrs['__delete__'] = "delete from '%s' where '%s'=?" % (table_name, primary_key)
        return type.__new__(mcs, name, bases, attrs)


class Model(dict, mateclass=ModelMate):

    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def get_value(self,key):
        return getattr(self, key, None)

    def get_value_or_default(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value =  field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' % (key, str(value)))
                setattr(self, key, value)
        return value


    @classmethod
    async def find_all(cls, where=None, args=None, **kw):
        """
        查询集合函数
        :param where: 索引条件
        :param args:
        :param kw:
        :return:
        """
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []
        order_by = kw.get('orderBy', None)
        if order_by:
            sql.append('order by')
            sql.append(order_by)
        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?,?')
                args.extend(limit) # 这里涉及到了list的extend方法和append方法的使用区别。
            else:
                raise ValueError('Invalid limit value : %s' % str(limit))
        rs = await select(' '.join(sql), args)
        # await 是和 async配合使用，@asyncio.coroutine 是和 yield from 配合使用
        # rs = yield from select(' '.join(sql), args)
        return [cls(**r) for r in rs]

    # 后续在添加完善其它函数，这里先做占位
    @classmethod
    async def find_number(cls, selected_field, where=None, ):
        pass
