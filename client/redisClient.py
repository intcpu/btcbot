#!/usr/bin/env python3
# encoding: utf-8

import redis

class RedisQueue(object):
    queue_pre   = 'queue:'

    def setQueueKey(self, key):
        self.queue_key = self.queue_pre + key

    def qsize(self, key):
        self.setQueueKey(key)
        return self._db.llen(self.queue_key)  # 返回队列里面list内元素的数量

    def put(self, key, data):
        self.setQueueKey(key)
        self._db.rpush(self.queue_key, data)  # 添加新元素到队列最右方

    def pop(self, key):
        self.setQueueKey(key)
        # 直接返回队列第一个元素，如果队列为空返回的是None
        data = self._db.lpop(self.queue_key)  
        return data
    def get(self, key):
        self.setQueueKey(key)
        # 返回队列所有值
        data = self._db.lrange(self.queue_key, 0, -1)
        return data

    def pop_wait(self, key, timeout=None):
        self.setQueueKey(key)
        # 返回队列第一个元素，如果为空则等待至有元素被加入队列（超时时间阈值为timeout，如果为None则一直等待）
        data = self._db.blpop(self.queue_key, timeout=timeout)
        # if data:
        #     data = data[1]  # 返回值为一个tuple
        return data

class RedisHash(object):
    hash_pre = 'hash:'

    def setHashKey(self, key):
        self.hash_key = self.hash_pre + key
    
    def hset(self, key, keys, data):
        self.setHashKey(key)
        self._db.hset(self.hash_key, keys ,data)  # 添加新元素到队列最右方
        
    def hget(self, key, keys):
        self.setHashKey(key)
        return self._db.hget(self.hash_key, keys)

    def hmset(self, key, data):
        self.setHashKey(key)
        return self._db.hmset(self.hash_key, data)        

    def hgetall(self, key):
        self.setHashKey(key)
        return self._db.hgetall(self.hash_key)

class RedisStr(object):
    str_pre = 'str:'

    def setStrKey(self, key):
        self.str_key = self.str_pre + key

    def set(self, key, val):
        self.setStrKey(key)
        self._db.set(self.str_key ,val)

    def get(self, key):
        self.setStrKey(key)
        return self._db.get(self.str_key)

    def delete(self, key):
        self.setStrKey(key)
        return self._db.delete(self.str_key)

class redisClient(RedisStr,RedisHash,RedisQueue):
    def __init__(self, namespace='py', redis_host='127.0.0.1', redis_port=6379, redis_db=0):
        self._db = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)
        self.str_pre = '%s:%s' % (namespace, self.str_pre)
        self.hash_pre = '%s:%s' % (namespace, self.hash_pre)
        self.queue_pre = '%s:%s' % (namespace, self.queue_pre)

if __name__ == '__main__':
    redis_db = redisClient(namespace='bm')
    btc_data = redis_db.hset('lever:risk:test',1,1)
    btc_data = redis_db.hgetall('lever:risk:test')
    print(btc_data)