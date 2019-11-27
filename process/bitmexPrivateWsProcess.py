# encoding: utf-8
import logging,traceback,time
from process import config
from api.bitmexWebsocket import bitmexWebsocket
from process.processInterface import processInterface

class bitmexPrivateWsProcess(processInterface):
    PRO_CNAME = 'privateWss'
    PRO_DATA  = 'data'
    def __init__(self, symbols=config.PRI_SYMBOLS, api_key=config.API_KEY, api_secret=config.API_SECRET, test_net=config.TEST_NET):
        """"""
        self.api_key    = api_key
        self.api_secret = api_secret
        self.symbols    = symbols
        self.test_net   = test_net

        self.set_time   = {'order':0,'position':0,'margin':0}
        self.last_time  = {'order':0,'position':0,'margin':0}
        self.times      = {'order':0,'position':0,'margin':0}

    def init(self, master, user):
        self.master = master
        self.user   = user
        self.master.set_pro_name(self.PRO_CNAME)

        self.btWss = bitmexWebsocket()
        self.btWss.public_subs = []
        # self.btWss.public_subs  = ['trade','tradeBin1m','tradeBin5m','tradeBin1h','tradeBin1d','orderBook10','funding']
        self.btWss.private_subs = ['order','position','margin']
        # self.btWss.callback_dict = {'tradeBin1m':formatData.tradeBin1m}
        self.btWss.on_error = self.on_error_ws
        self.btWss.on_disconnected = self.on_disconnected
        self.btWss.on_action = self.wss_action
        self.btWss.connect(symbols=self.symbols, api_key=self.api_key, api_secret=self.api_secret, test_net=self.test_net, proxy_host=config.PROXY_HOST, proxy_port=config.PROXY_PORT)

    def wss_action(self, action, table, symbol):
        self.master.check_gid()
        try:
            if table in self.btWss.private_subs:
                data = self.reset_time(table,self.btWss.data)
                self.master.set_glob(self.user.USER,data)
            else:
                self.master.set_glob(self.user.TRADE,self.btWss.data)
        except:
            logging.info('{} wss try except'.format(self.PRO_CNAME))
            self.master.sysError()

    #重置时间
    def reset_time(self,table,data):
        now_time = int(time.time())
        if self.last_time[table] != now_time:
            self.last_time[table]  = now_time
            self.times[table] = 0
        else:
            self.times[table] += 1

        self.set_time[table] = self.last_time[table] + (self.times[table]/100)
        data['time'] = self.set_time
        return data

    def on_disconnected(self):
        """连接回调"""
        self.master.ding('{} Websocket API连接断开'.format(self.PRO_CNAME))
        self.btWss.subscribe()
        self.btWss.authenticate()

    def on_error_ws(self, exception_type, exception_value, tb):
        text = "".join(
            traceback.format_exception(exception_type, exception_value, tb)
        )
        logging.error(text)
        self.master.ding('{} 进程终止'.format(self.PRO_CNAME))
        self.master.kill_me()