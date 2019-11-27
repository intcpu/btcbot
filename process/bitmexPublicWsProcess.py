# encoding: utf-8
import logging,traceback
from process import config
from api.bitmexWebsocket import bitmexWebsocket
from process.processInterface import processInterface

class bitmexPublicWsProcess(processInterface):
    PRO_CNAME = 'publicWss'
    PRO_DATA = 'data'
    def __init__(self):
        """"""
        pass

    def init(self,master,user):
        self.master = master
        self.user   = user
        self.master.set_pro_name(self.PRO_CNAME)

        self.btWss = bitmexWebsocket()
        self.btWss.public_subs  = ['trade','tradeBin1m','tradeBin5m','tradeBin1h','tradeBin1d','orderBook10','funding']
        self.btWss.private_subs = []
        # self.btWss.callback_dict = {'tradeBin1m':formatData.tradeBin1m}
        self.btWss.on_error = self.on_error_ws
        self.btWss.on_disconnected = self.on_disconnected
        self.btWss.on_action = self.wss_action
        self.btWss.connect(symbols=config.PUB_SYMBOLS, test_net=config.TEST_NET, proxy_host=config.PROXY_HOST, proxy_port=config.PROXY_PORT)

    def wss_action(self, action, table, symbol):
        self.master.check_gid()
        try:
            self.master.set_glob(self.user.TRADE,self.btWss.data)
        except:
            logging.info('{} wss try except'.format(self.PRO_CNAME))
            self.master.sysError()

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