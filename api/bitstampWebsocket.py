# encoding: UTF-8

import logging
from client.websocketClient import websocketClient


BITSTAMP_HOST = 'wss://ws.bitstamp.net'

class bitstampWebsocket(websocketClient):
    """"""

    MAX_TABLE_LEN = 100

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super().__init__()
        #
        self.apiKey = ''
        self.apiSecret = ''
        self.symbols = []
        self.data = {}
        
    #----------------------------------------------------------------------
    def connect(self, symbols, proxy_host=None, proxy_port=None):
        """"""
        self.init(BITSTAMP_HOST, proxy_host, proxy_port)

        self.start()

        for symbol in symbols:
            self.symbols.append(symbol)

    #----------------------------------------------------------------------
    def on_connected(self):
        """连接回调"""
        logging.info(u'Websocket API连接成功')
        self.subscribe()
    
    #----------------------------------------------------------------------
    def on_disconnected(self):
        """连接回调"""
        logging.info(u'Websocket API连接断开')
        self.subscribe()
    
    #----------------------------------------------------------------------
    def on_packet(self, packet):
        logging.info('-----packet-----')
        """数据回调"""
        if 'error' in packet:
            logging.error(u'Websocket API报错：%s' %packet['error'])
            
            if 'not valid' in packet['error']:
                self._active = False
        elif 'data' in packet:
            print(packet['data'])
    
    #----------------------------------------------------------------------
    def on_error(self, exception_type, exception_value, tb):
        """Python错误回调"""
        msg = f"触发异常，状态码：{exception_type}，信息：{exception_value}"
        logging.error(msg)

        logging.error(
            self.exception_detail(exception_type, exception_value, tb, request)
        )

    #----------------------------------------------------------------------
    def subscribe(self):
        """"""
        args = ['live_trades', 'live_orders', 'detail_order_book']
        for symbol in self.symbols:
            for arg in args:
                req = {
                    "event": "bts:subscribe",
                    "data": {
                        "channel": '_'.join([arg, symbol])
                    }
                }
                self.send_packet(req)

if __name__ == '__main__':
    bt = bitstampWebsocket()
    bt.connect(['btcusd', 'ethusd', 'bchusd'])
