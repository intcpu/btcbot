# encoding: UTF-8
import sys
import logging,time,json
import hashlib,hmac
from client.websocketClient import websocketClient

REST_HOST = 'https://www.bitmex.com/api/v1'
TESTNET_REST_HOST = 'https://testnet.bitmex.com/api/v1'

WEBSOCKET_HOST = 'wss://www.bitmex.com/realtime'
TESTNET_WEBSOCKET_HOST = 'wss://testnet.bitmex.com/realtime'

class bitmexWebsocket(websocketClient):
    """"""
    MAX_TABLE_LEN = 120

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super().__init__()
        #
        self.api_key    = ''
        self.api_secret = ''

        # self.public_subs  = ['trade','instrument','tradeBin1m','tradeBin5m','tradeBin1h','tradeBin1d','orderBook10','funding']
        # self.private_subs = ['order','position','margin']
        self.public_subs   = []
        self.private_subs  = []
        self.callback_dict = {}

        self.symbols = []
        self.keys    = {}
        self.data    = {'time': 0}

    #----------------------------------------------------------------------
    def connect(self,symbols=[],api_key='',api_secret='',test_net=True,proxy_host=None, proxy_port=None):
        """"""
        self.symbols = symbols if isinstance(symbols, list) else [symbols]

        self.api_key = api_key
        self.api_secret = api_secret

        if not test_net:
            self.init(WEBSOCKET_HOST,proxy_host,proxy_port)
        else:
            self.init(TESTNET_WEBSOCKET_HOST,proxy_host,proxy_port)

        self.start()


    #----------------------------------------------------------------------
    def on_connected(self):
        """连接回调"""
        logging.info(u'Websocket API连接成功')
        self.subscribe(self.public_subs)
        self.authenticate()

    
    #----------------------------------------------------------------------
    def on_disconnected(self):
        """连接回调"""
        logging.info(u'Websocket API连接断开')

    def on_packet(self, message):
        if 'error' in message:
            logging.error(u'WS ERROR：%s' % message['error'])
            if 'not valid' in message['error']:
                self._active = False
        elif 'request' in message:
            req = message['request']
            success = message['success']
            if success:
                if req['op'] == 'authKeyExpires':
                    logging.info('AUTH TRUE')
                    self.private_subs and self.subscribe(self.private_subs)
                if 'subscribe' in message:
                    logging.info("Subscribed to %s." % message['subscribe'])
        elif 'table' in message:
            table = message['table'] if 'table' in message else None
            action = message['action'] if 'action' in message else None
            try:
                if action:
                    symbol = message['data'][0]['symbol'] if len(message['data']) > 0 and 'symbol' in message['data'][0] else None

                    if table not in self.data:
                        self.data[table] = {}
                    if symbol and symbol not in self.data[table]:
                        self.data[table][symbol] = []

                    # There are four possible actions from the WS:
                    # 'partial' - full table image  全量获取
                    # 'insert'  - new row           新的一行
                    # 'update'  - update row        更新
                    # 'delete'  - delete row        删除

                    if table == 'margin':
                        if action == 'partial':
                            self.data[table] = message['data'][0]
                        elif action == 'update':
                            self.data[table].update(message['data'][0])
                    elif action == 'partial':
                        if len(message['data']) > 0:
                            self.data[table][symbol] += message['data']
                        self.keys[table] = message['keys']
                    elif action == 'insert':
                        self.data[table][symbol] += message['data']
                        # 多余数量删除一半
                        if len(self.data[table][symbol]) > self.MAX_TABLE_LEN:
                            self.data[table][symbol] = self.data[table][symbol][(0-int(self.MAX_TABLE_LEN / 2)):]
                    elif action == 'update':
                        for updateData in message['data']:
                            item = self.findItemByKeys(self.keys[table], self.data[table][symbol], updateData)
                            if not item:
                                return  # No item found to update. Could happen before push
                            item.update(updateData)
                            # Remove cancelled / filled orders
                            if table == 'order' and item['leavesQty'] <= 0:
                                self.data[table][symbol].remove(item)
                    elif action == 'delete':
                        for deleteData in message['data']:
                            item = self.findItemByKeys(self.keys[table], self.data[table][symbol], deleteData)
                            self.data[table][symbol].remove(item)
                else:
                    logging.error("Unknown action: %s" % action)
                self.data['time'] = int(time.time())

                if table in self.callback_dict:
                    callback = self.callback_dict[table]
                    callback(message['data'])

                self.on_action(action,table,symbol)
            except:
                logging.info(message)
                t, v, tb = sys.exc_info()
                self.on_error(t, v, tb)

    #用户操作
    def on_action(self,action,table,symbol):
        # logging.info('---on_action---')
        pass

    #----------------------------------------------------------------------
    def on_error(self, exception_type, exception_value, tb):
        """Python错误回调"""
        msg = f"触发异常，状态码：{exception_type}，信息：{exception_value}"
        logging.error(msg)

        #----------------------------------------------------------------------
    def jsonlog(self, content):
        """发出日志"""
        try:
            logging.info(json.dumps(content, sort_keys=True, indent=4, separators=(', ', ': ')))
        except:
            logging.info(content)

    #----------------------------------------------------------------------
    def authenticate(self):
        if not self.api_key or not self.api_secret:
            return
        expires = int(time.time()) + 60
        method = 'GET'
        path = '/realtime'
        msg = method + path + str(expires)

        signature = hmac.new(self.api_secret.encode('utf-8'), msg.encode('utf-8'), digestmod=hashlib.sha256).hexdigest()
        
        req = {
            'op': 'authKeyExpires', 
            'args': [self.api_key, expires, signature]
        }
        self.send_packet(req)

    #----------------------------------------------------------------------
    def subscribe(self,subs=None):
        """"""
        sub_margin = False
        subs = subs if subs else self.public_subs
        for symbol in self.symbols:
            req = {
                'op': 'subscribe',
                'args': []
            }
            for arg in subs:
                if arg not in ['margin']:
                    req['args'].append(':'.join([arg, symbol]))
                elif sub_margin is False:
                    req['args'].append(arg)
                    sub_margin = True
            self.send_packet(req)

    #确定后续数据与第一次数据的交易对symbol 或其他keys值保持一致
    def findItemByKeys(self,keys, table, matchData):
        for item in table:
            matched = True
            for key in keys:
                if item[key] != matchData[key]:
                    matched = False
            if matched:
                return item

if __name__ == '__main__':
    PROXY_HOST = '127.0.0.1'
    PROXY_PORT = 8118
    SYMBOL = 'XBTUSD'
    # ceshi
    API_KEY = ''
    API_SECRET = ''
    logging.basicConfig(filename="logs/log", filemode="w", format="%(asctime)s %(name)s:%(levelname)s:%(message)s",
                        level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")

    bt = bitmexWebsocket()
    bt.connect([SYMBOL], API_KEY, API_SECRET, True)
    while True:
        for d in bt.data:
            if d != 'trade':
                bt.jsonlog(bt.data[d])
        time.sleep(10)



