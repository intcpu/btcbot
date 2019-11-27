# encoding: utf-8
import sys,traceback
import time,logging
import operator
from process.processInterface import processInterface
from strategy.testStrategy import testStrategy

class strategyProcess(processInterface):
    PRO_CNAME = 'strategy'
    PRO_DATA  = 'data'

    def __init__(self):
        """"""
        self.is_lock   = 0
        self.last_time = 0
        self.data = {}
        self.kline = {}

    def lock(self):
        if self.is_lock > 0:
            return False
        else:
            self.is_lock = 1
            return True

    def unlock(self):
        if self.is_lock > 0:
            self.is_lock = 0
            return True
        else:
            return False

    def set_time(self):
        self.last_time = int(time.time())

    def init(self, master, user):
        self.master = master
        self.user = user
        self.master.set_pro_name(self.PRO_CNAME)

        self.init_status()
        self.test = testStrategy()
        while True:
            try:
                self.lock()
                self.master.check_gid()
                self.set_time()
                self.getUser()
                self.checkUser()
                self.unlock()
            except Exception as error:
                logging.info(error)
                # self.error()
            try:
                if self.lock():
                    self.test.init(self.margin, self.position, self.order, self.kline)
                    orders = self.test.get_order()
                    status = self.master.lock_glob(self.user.STATUS)
                    if status == 3:
                        status, orders = self.reset_order(status, orders)
                    if status == 0 and orders:
                        # logging.info(self.margin)
                        # logging.info(self.position)
                        # logging.info(self.order)
                        self.order['new'] = orders
                        self.master.set_glob(self.user.ORDER, self.order)
                        self.master.lock_glob(self.user.STATUS,1)
                time.sleep(10)
            except:
                self.master.sysError()

    def init_status(self):
        if self.master.lock_glob(self.user.STATUS) is None:
            self.master.lock_glob(self.user.STATUS, 0)

    def reset_order(self, status, orders):
        if orders:
            keys = list(orders.keys())
            for key in keys:
                if key in self.order['new'] and operator.eq(self.order['new'][key], orders[key]):
                    del orders[key]
            if orders:
                logging.info('fail order not resend')
            elif self.margin['order_cost'] == 0 and self.position['order_cost'] == 0 and (self.order['buy_num'] + self.order['sell_num']) == 0:
                logging.info('no order_cost,reset order status')
            else:
                return status, orders
        else:
            logging.info('no orders,reset order status')

        self.master.lock_glob(self.user.STATUS, 0)
        # return 0,orders
        # 下次从来
        return status,orders

    def getUser(self):
        self.order = self.master.get_glob(self.user.ORDER)
        self.position = self.master.get_glob(self.user.POSITION)
        self.margin = self.master.get_glob(self.user.MARGIN)
        self.kline = self.master.get_glob(self.user.KLINE)

    def checkUser(self):
        if not self.margin or not self.position or not self.order:
            raise Exception('data is not init')

        if self.margin['order_cost'] > 0:
            if not self.order or (self.order['buy_num']+self.order['sell_num']) == 0:
                raise Exception('order not init')

        if self.margin['margin_cost'] > 0 and self.position['num'] == 0:
            raise Exception('position is not init')

        if 'last_buy' not in self.position:
            raise Exception('trade not init')

        if self.margin['order_cost']  != self.position['order_cost']:
            logging.info({'order_cost':self.margin['order_cost'],'p_order_cost':self.position['order_cost']})
            raise Exception('position and margin order_cost is not sync')

        # if self.order['buy_num'] != self.position['buy_num'] or self.order['sell_num'] != self.position['sell_num']:
        #     raise Exception('position and order is not sync')

    def error(self):
        t, v, tb = sys.exc_info()
        text = "".join(
            traceback.format_exception(t, v, tb)
        )
        logging.info(text)