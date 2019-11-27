# encoding: utf-8
import os,sys
sys.path.append('..')
import time, logging, demjson, datetime, math
from backtest import config
import pandas as pd
from strategy.testStrategy import testStrategy

class testuserProcess():
    PRO_CNAME = 'testuser'

    def __init__(self, margin=0, lv=10):
        self.margin = demjson.decode("{'all_num': 0, 'order_cost': 0, 'margin_cost': 0, 'over_cost': 0}")
        self.position = demjson.decode("{'num': 0, 'lv': 1, 'price': 0, 'liqun_price': 0, 'last_buy': 0, 'last_sell': 0}")
        self.order = demjson.decode("{'all': [], 'buy_out': 0, 'sell_out': 0}")

        self.orderID = 1
        self.all_num = self.XBT_to_XBt(margin)
        self.margin['all_num'] = self.XBT_to_XBt(margin)
        self.margin['over_cost'] = self.margin['all_num']
        self.position['lv'] = lv
        self.kline = {'tradeBin5m': []}

        self.tests = testStrategy()

    def test(self):
        modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
        datapath_1 = os.path.join(modpath, '../data/xbt_bitmex_60.csv')
        dataframe_1 = pd.read_csv(datapath_1, header=None, index_col=None, parse_dates=['timestamp'], date_parser=dateToStr, names=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        # dataframe_1 = dataframe_1[0:10000]
        start = time.time()
        tradeBin5m = []
        for index, row in dataframe_1.iterrows():

            self.position['last_buy'] = row['close']-config.MIN_PRICE
            self.position['last_sell'] = row['close']+config.MIN_PRICE

            new_row = {'timestamp': str(row['timestamp']), 'open': float(row['open']), 'high': float(row['high']), 'low': float(row['low']), 'close': float(row['close']), 'volume': float(row['volume'])}
            tradeBin5m.append(new_row)
            if len(tradeBin5m) > 120:
                tradeBin5m = tradeBin5m[60:]
            self.kline['tradeBin5m'] = tradeBin5m

            self.position_pre()
            self.order_pre()
            self.margin_init()

            self.tests.init(self.margin, self.position, self.order, self.kline)
            orders = self.tests.get_order()
            self.order_suf(orders)

        end = time.time()
        print('----profit---')
        print(self.margin['all_num'] - self.all_num)
        print('----margin---')
        print(self.margin)
        print('----position---')
        print(self.position)
        print('----order---')
        print(self.order)
        print('----time---')
        print(end-start)

    def init(self, master, user):
        self.master = master
        self.user = user
        self.master.set_pro_name(self.PRO_CNAME)
        while True:
            try:
                # self.master.check_gid()
                time.sleep(1)
            except:
                self.master.sysError()

    #爆仓
    def position_pre(self):
        if self.position['num'] == 0:return

        if self.position['liqun_price'] <= self.kline['tradeBin5m'][-1]['high'] and self.position['liqun_price'] >= self.kline['tradeBin5m'][-1]['low']:
            print('!!!!!!!!!!beng bigin!!!!!!!!!')
            print(self.margin)
            print(self.position)
            print(self.order)
            margin = self.open_margin(self.position['num'], self.position['price'])
            self.margin['all_num'] -= margin
            self.margin['margin_cost'] = 0
            self.margin['order_cost'] = 0
            self.margin['over_cost'] = self.margin['all_num']

            self.position['price'] = 0
            self.position['num'] = 0
            self.position['liqun_price'] = 0

            self.order = {'all': [], 'buy_out': 0, 'sell_out': 0}

            print(self.kline)
            print(self.margin)
            print('!!!!!!!!!!beng end!!!!!!!!!')

    #成交
    def order_pre(self):
        if len(self.order['all']) == 0: return

        new_orders = []
        for i in range(0, len(self.order['all'])):
            o = self.order['all'][i]
            if o['price'] <= self.kline['tradeBin5m'][-1]['high'] and o['price'] >= self.kline['tradeBin5m'][-1]['low']:
                orderQty = o['orderQty'] if o['side'] == 'Buy' else -o['orderQty']
                # margin = self.open_margin(o['orderQty'], o['price'])
                num = self.position['num'] + orderQty

                if self.position['num']*orderQty > 0:
                    self.position['price'] =  math.ceil((self.position['price']*abs(self.position['num'])+(o['orderQty']*o['price']))/(abs(self.position['num'])+o['orderQty']))
                elif self.position['num']*orderQty < 0:
                    if num * self.position['num'] < 0:
                        close_num = self.position['num']
                        self.position['price'] = o['price']
                    else:
                        close_num = o['orderQty']
                    # close_margin = self.open_margin(close_num, self.position['price'])
                    close_profit = self.profit(close_num, self.position['price'], o['price'])
                    self.margin['all_num'] += close_profit
                else:
                    self.position['price'] = o['price']
                self.position['num'] = num
                self.position['liqun_price'] = self.liqui_price(self.position['num'], self.position['price']) if self.position['num'] != 0 else 0
            else:
                new_orders.append(o)

        self.order['all'] = new_orders

    #保证金初始化
    def margin_init(self):
        if self.margin['order_cost'] + self.margin['margin_cost'] + self.margin['over_cost'] != self.margin['all_num']:
            self.margin['order_cost'] = self.order_cost(self.order['all'])
            self.margin['margin_cost'] = self.open_margin(self.position['num'], self.position['price'])
            self.margin['over_cost'] = self.margin['all_num'] - self.margin['order_cost'] - self.margin['margin_cost']

            if self.margin['over_cost'] < 0:
                logging.error('margin error')
                print('-------diff------')
                print(self.margin['order_cost'] + self.margin['margin_cost'] - self.margin['all_num'])
                print('-------margin------')
                print(self.margin)
                print('-------position------')
                print(self.position)
                print('-------open_margin------')
                print(self.open_margin(self.position['num'], self.position['price']))
                print('-------order------')
                print(self.order)
                print('-------order_cost------')
                print(self.order_cost(self.order['all']))
                print('-------kline------')
                print(self.kline)
                raise Exception('margin error')

    #下单
    def order_suf(self, orders):
        if not orders: return
        orderid = int(datetime.datetime.now().strftime("%Y%m%d"))*1000000000

        new_all = self.order['all'].copy()

        for key, val in orders.items():
            if key == 'add_order':
                for o in val:
                    o['orderID'] = orderid+self.orderID
                    o['leavesQty'] = o['orderQty']
                    o['cumQty'] = 0
                    new_all.append(o)
                    self.orderID += 1
            elif key == 'up_order':
                for o in val:
                    for i in range(0, len(new_all)):
                        if o['orderID'] == new_all[i]['orderID']: new_all[i].update(o)
            elif key == 'del_order':
                new_orders = []
                for o in val:
                    for i in range(0, len(new_all)):
                        if o['orderID'] != new_all[i]['orderID']: new_orders.append(new_all[i])
                new_all = new_orders.copy()
        self.reset_margin(new_all)

    #仓位保证金
    def reset_margin(self, new_all):
        cost = self.order_cost(new_all)

        if self.position['num'] != 0:
            self.position['margin_cost'] = self.open_margin(self.position['num'], self.position['price'])
        else:
            self.position['margin_cost'] = 0

        if self.position['margin_cost'] + cost <= self.margin['all_num']:
            self.margin['order_cost'] = cost
            self.margin['over_cost'] = self.margin['all_num'] - self.position['margin_cost'] - cost
            self.order['all'] = new_all
        else:
            # print(new_all)
            # print(self.margin)
            # print(order_cost)
            # logging.error('over_cost is short')
            pass

    # 下单保证金
    def order_cost(self, new_all):
        new_all_buy = [o for o in sorted(new_all, key=lambda x: x['price'], reverse=True) if o['side'] == 'Buy']
        new_all_sell = [o for o in sorted(new_all, key=lambda x: x['price'], reverse=False) if o['side'] == 'Sell']

        sell_cost = 0
        now_num = self.position['num']
        for o in new_all_sell:
            if now_num > 0:
                open_num = o['orderQty']
                if open_num > now_num:
                    num = open_num-now_num
                    sell_cost += self.open_margin(num, o['price'])
                    now_num = 0
                else:
                    now_num -= open_num
            else:
                sell_cost += self.open_margin(o['orderQty'], o['price'])

        buy_cost = 0
        for o in new_all_buy:
            if now_num < 0:
                open_num = o['orderQty']
                if open_num > abs(now_num):
                    num = open_num+now_num
                    buy_cost += self.open_margin(num, o['price'])
                    now_num = 0
                else:
                    now_num += open_num
            else:
                buy_cost += self.open_margin(o['orderQty'], o['price'])

        cost = max(buy_cost, sell_cost)
        return cost

    def XBt_to_XBT(self,XBt):
        return float(XBt) / config.XBT_UNIT

    def XBT_to_XBt(self,XBT):
        return int(XBT*config.XBT_UNIT)

    #开仓价值
    def open_val(self,qty,price):
        return abs(int(qty/price*config.XBT_UNIT))

    #开仓保证金
    def open_margin(self,qty,price,mark=True):
        free = config.MAKER_FEE if mark else config.TAKER_FEE
        val = self.open_val(qty,price)
        val = (1/self.position['lv']+free)*val
        return int(val)
    #维持
    def main_margin(self,qty,price):
        val = self.open_val(qty,price)
        val = (config.MAINT_MARGIN+config.TAKER_FEE)*val
        return int(val)
    #爆仓价
    def liqui_price(self,qty,price):
        m = self.main_margin(qty,price)
        b = self.open_margin(qty,price)
        close = 1/((1/price) - ((m-b)/config.XBT_UNIT/qty))
        return int(close)
    #盈利
    def profit(self,qty,price,close):
        return int(qty*(1/price - 1/close)*config.XBT_UNIT)

    #kaili
    def kaili(self,price,close,liqui,p):
        Rw = abs(close - price)/price
        Rl = abs(price - liqui)/price
        b  = Rw/Rl
        f=(p*Rw-(1-p)*Rl)/(Rl*Rw)
        return [b,f]

def dateToStr(dateline):
    timeArray = time.localtime(int(dateline))
    dateStr  = time.strftime("%Y-%m-%d %H:%M:%S",timeArray)
    return dateStr

if __name__ == '__main__':
    logging.basicConfig(
        filename="../logs/" + time.strftime("%Y%m%d") + '.log',
        filemode="a",
        format="%(asctime)s %(name)s:%(levelname)s:%(message)s",
        level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S"
    )
    user = testuserProcess(margin=1)
    m = user.test()