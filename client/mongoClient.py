# encoding: UTF-8
import logging
from datetime import datetime
from pymongo import MongoClient,ASCENDING,DESCENDING
from pymongo import InsertOne, DeleteOne,ReplaceOne,UpdateOne
from pymongo.errors import ConnectionFailure

class mongoClient(object):
    def __init__(self, mongo_host='127.0.0.1', mongo_port=27017):
        # 记录今日日期
        self.todayDate = datetime.now().strftime('%Y%m%d')
        # MongoDB数据库相关
        self.dbClient = None    # MongoDB客户端对象

        self.mongo_host = mongo_host
        self.mongo_port = mongo_port
        self.time_out   = 500

    #----------------------------------------------------------------------
    def connect(self):
        """连接MongoDB数据库"""
        if not self.dbClient:
            # 读取MongoDB的设置
            try:
                # 设置MongoDB操作的超时时间为0.5秒
                self.dbClient = MongoClient(self.mongo_host, self.mongo_port, connectTimeoutMS=self.time_out)
                
                # 调用server_info查询服务器状态，防止服务器异常并未连接成功
                self.dbClient.server_info()

                logging.info('mongo 连接成功')
                    
            except ConnectionFailure:
                logging.error('mongo 连接失败')
    
    #----------------------------------------------------------------------
    def insert_one(self, dbName, collectionName, d):
        """向MongoDB中插入数据，d是具体数据"""
        if self.dbClient:
            db = self.dbClient[dbName]
            collection = db[collectionName]
            collection.insert_one(d)
        else:
            logging.error('mongo 插入失败')

    #----------------------------------------------------------------------
    def insert_many(self, dbName, collectionName, d):
        """向MongoDB中插入数据，d是具体数据"""
        if self.dbClient:
            db = self.dbClient[dbName]
            collection = db[collectionName]
            collection.insert_many(d)
        else:
            logging.error('mongo 插入失败')

    #创建索引
    def create_index(self, dbName, collectionName, d):
        if self.dbClient:
            db = self.dbClient[dbName]
            collection = db[collectionName]
            collection.create_index(d)
        else:
            logging.error('mongo 插入失败')

    #创建索引
    def unique_index(self, dbName, collectionName, d):
        if self.dbClient:
            db = self.dbClient[dbName]
            collection = db[collectionName]
            collection.create_index(d,unique=True)
        else:
            logging.error('mongo 插入失败')

    #----------------------------------------------------------------------
    # ASCENDING DESCENDING
    def find(self, dbName, collectionName, d, sortKey='', sortDirection='desc',limit=None):
        """从MongoDB中读取数据，d是查询要求，返回的是数据库查询的指针"""
        if self.dbClient:
            db = self.dbClient[dbName]
            collection = db[collectionName]
            
            if sortDirection == 'desc':
                sortDirection = DESCENDING
            else:
                sortDirection = ASCENDING
            if sortKey and limit:
                cursor = collection.find(d).sort(sortKey, sortDirection).limit(limit)
            elif sortKey:
                cursor = collection.find(d).sort(sortKey, sortDirection)    # 对查询出来的数据进行排序
            elif limit:
                cursor = collection.find(d).limit(limit)
            else:
                cursor = collection.find(d)

            if cursor:
                return list(cursor)
            else:
                return []
        else:
            logging.error('mongo数据查询失败')   
            return []
        
    #----------------------------------------------------------------------
    def update(self, dbName, collectionName, d, flt, upsert=False):
        """向MongoDB中更新数据，d是具体数据，flt是过滤条件，upsert代表若无是否要插入"""
        if self.dbClient:
            db = self.dbClient[dbName]
            collection = db[collectionName]
            collection.replace_one(flt, d, upsert)
        else:
            logging.error('mongo数据更新失败')   

    #----------------------------------------------------------------------
    def update_many(self, dbName, collectionName, d, key, upsert=False):
        """向MongoDB中更新数据，d是具体数据，flt是过滤条件，upsert代表若无是否要插入"""
        if self.dbClient:
            db = self.dbClient[dbName]
            collection = db[collectionName]

            ns = []
            for i in d:
                ns.append(ReplaceOne({key: i[key]}, i, upsert=True))
            if len(ns) > 0:
                res = collection.bulk_write(ns)
        else:
            logging.error('mongo数据更新失败')   
    
    #----------------------------------------------------------------------
    def delete(self, dbName, collectionName, flt):
        """从数据库中删除数据，flt是过滤条件"""
        if self.dbClient:
            db = self.dbClient[dbName]
            collection = db[collectionName]
            collection.delete_one(flt)
        else:
            logging.error('mongo数据删除失败')

    #----------------------------------------------------------------------
    def drop_coll(self, dbName, collectionName):
        """从数据库中删除数据，flt是过滤条件"""
        if self.dbClient:
            db = self.dbClient[dbName]
            collection = db[collectionName]
            collection.remove()
        else:
            logging.error('mongo数据删除失败')


if __name__ == '__main__':

    mongo_db  = mongoClient()
    mongo_db.connect()
    mongo_db.insert_one('bitmex','test',{'name':'aaa','age':15,'price':5000})
    mongo_db.insert_one('bitmex','test',{'name':'bbb','age':18,'price':3000})
    mongo_db.insert_one('bitmex','test',{'name':'ccc','age':20,'price':1000})
    btc_data = mongo_db.find('bitmex','test',{'age':{'$gte':15}})
    print(btc_data)