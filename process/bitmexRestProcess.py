# encoding: utf-8
import os,sys
import logging,time,traceback
from process import config
from process.processInterface import processInterface
from api.bitmexRequest import bitmexRequest

class bitmexRestProcess(processInterface):
    PRO_CNAME = 'bitmexRest'

    def __init__(self, api_key=config.API_KEY, api_secret=config.API_SECRET, test_net=config.TEST_NET, proxy_host=config.PROXY_HOST, proxy_port=config.PROXY_PORT):
        """
        每次只允许一个请求
        """
        self.api_key     = api_key
        self.api_secret  = api_secret
        self.test_net    = test_net
        self.proxy_host  = proxy_host
        self.proxy_port  = proxy_port
        self.session_num = 3

        self.kline      = {}
        self.orders     = {}

        #锁
        self.is_lock = 0
        #最小执行锁
        self.min_lock = 1
        #最后完成时间
        self.last_time = 0
        #连续错误次数
        self.error_time = 0
        #最后错误信息
        self.last_error = ''

        self.bmxRest = None

    def init(self, master, user):
        self.master = master
        self.user   = user
        self.master.set_pro_name(self.PRO_CNAME)
        self.dd = self.master.dd

        self.start()
        self.init_kline()

        while True:
            try:
                self.master.check_gid()
                if self.is_lock == 0:
                    if self.error_time > 2:
                        self.master.sysError()
                        self.master.kill_me()
                    elif self.last_error:
                        self.dd.msg(self.last_error)
                        self.last_error = ''

                    orders = self.master.get_glob(self.user.ORDER)
                    status = self.master.lock_glob(self.user.STATUS)
                    if status == 2:
                        for key in self.orders.keys():
                            logging.info('{} is fail'.format(key))
                            del orders['new'][key]
                        self.master.set_glob(self.user.ORDER, orders)
                        self.master.lock_glob(self.user.STATUS, 3)
                    elif orders and self.last_time < orders['time'] and status == 1:
                        self.lock()
                        self.last_time = orders['time']

                        self.master.lock_glob(self.user.STATUS, 2)
                        self.orders = orders['new']

                        self.pushOrder()
                        self.unlock()
                time.sleep(1)
            except:
                self.unlock()
                self.master.sysError()

    def start(self):
        self.bmxRest = bitmexRequest()
        self.bmxRest.on_success = self.on_success
        self.bmxRest.on_send_order = self.on_send_order
        self.bmxRest.on_up_order = self.on_up_order
        self.bmxRest.on_cancel_order = self.on_cancel_order
        self.bmxRest.on_failed = self.on_failed
        self.bmxRest.on_error = self.on_error
        self.bmxRest.connect(self.api_key, self.api_secret, self.session_num, self.test_net, self.proxy_host, self.proxy_port)

    def lock(self):
        self.is_lock += 1
        return True

    def unlock(self):
        if self.is_lock > 0:
            self.is_lock -= 1
        if self.is_lock == self.min_lock:
            self.set_time()
        return True

    def set_time(self):
        self.last_time = int(time.time())

    def reset_error(self,msg):
        logging.info(msg)
        self.unlock()
        if self.is_lock == self.min_lock:
            self.error_time = 0
            self.last_error = ''

    def on_send_order(self, orders, request):
        del self.orders['add_order']
        self.reset_error('下单成功')

    def on_up_order(self, orders, request):
        del self.orders['up_order']
        self.reset_error('下单成功')

    def on_cancel_order(self, data, request):
        del self.orders['del_order']
        self.reset_error('取消订单成功')

    def on_success(self, data, request):
        if request.path == '/trade/bucketed':
            key = 'tradeBin{}'.format(request.params['binSize'])
            logging.info('{} success'.format(key))
            data.reverse()
            self.set_kline(key, data)
        self.reset_error('请求成功')

    def set_error(self, msg):
        logging.error(msg)
        self.error_time += 1
        self.last_error = msg
        self.unlock()


    def on_failed(self, status_code, request):
        try:
            response = request.response.json()
            if response['error']['name'] == 'ValidationError':
                del self.orders['add_order']
        except:
            pass

        msg = '请求失败，状态码：{}，信息：{}'.format(status_code, request.response.text)
        logging.error(msg)
        self.last_error = msg
        self.unlock()

        if status_code == 503:
            self.start()

    def on_error(self, exception_type, exception_value, tb, request):
        self.set_error('请求异常，状态码：{}，信息：{}'.format(exception_type,exception_value))


    def init_kline(self):
        if not self.bmxRest:
            logging.error('rest service is not start')
            return

        kdata = self.master.get_glob(self.user.KLINE)
        if kdata:
            self.kline = kdata
            logging.info('kline is set ,no init')
            logging.info(kdata)
            return
        try:
            self.bmxRest.trade_data({'symbol': 'XBTUSD', 'binSize': '5m'})
            self.bmxRest.trade_data({'symbol': 'XBTUSD', 'binSize': '1h'})
            self.bmxRest.trade_data({'symbol': 'XBTUSD', 'binSize': '1d', 'partial': True})
        except:
            t, v, tb = sys.exc_info()
            text = "".join(
                traceback.format_exception(t, v, tb)
            )
            logging.error(text)

    def set_kline(self, key, data):
        if key not in self.kline:
            self.kline[key] = data
        else:
            if len(self.kline[key]) > 0 and len(data) > 0:
                if self.kline[key][-1]['timestamp'] == data[0]['timestamp']:
                    del self.kline[key][-1]
            self.kline[key] += data

        self.master.set_glob(self.user.KLINE, self.kline)

    # 下单
    def pushOrder(self):
        if self.is_lock > self.min_lock or not self.bmxRest:
            return
        self.lock()
        logging.info('pushOrder is start')
        logging.info(self.orders)
        if 'del_order' in self.orders:
            self.lock()
            self.bmxRest.del_order(self.orders['del_order'])
            time.sleep(1)

        if 'up_order' in self.orders:
            self.lock()
            self.bmxRest.up_order(self.orders['up_order'])
            time.sleep(1)

        if 'add_order' in self.orders:
            self.lock()
            self.bmxRest.add_order(self.orders['add_order'])
        self.unlock()

