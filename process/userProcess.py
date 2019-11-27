# encoding: utf-8
import time
from process import config
from process.processInterface import processInterface

class userProcess(processInterface):
    PRO_CNAME = 'user'
    TRADE = 'trade'
    USER = 'user'
    KLINE = 'kline'
    ORDER = 'order'
    STATUS = 'status'
    POSITION = 'position'
    MARGIN = 'margin'

    def __init__(self):
        """"""
        self.last_time = 0
        self.kline_num = 60
        self.master = None

    def init(self, master):
        self.master = master
        self.master.set_pro_name(self.PRO_CNAME)

        while True:
            try:
                self.master.check_gid()
                trade = self.master.get_glob(self.TRADE)
                if trade:
                    self.init_kline(trade)
                user = self.master.get_glob(self.USER)
                if user and 'time' in user:
                    self.init_order(user)
                    self.init_margin(user)
                    self.init_position(user,trade)
                time.sleep(1)
            except:
                self.master.sysError()

    #初始化保证金
    def init_margin(self,user):
        if 'margin' not in user or 'margin' not in user['time']:
            return

        margin = self.master.get_glob(self.MARGIN)

        if not margin or 'time' not in margin:
            user_margin = {'time': user['time']['margin']}
        elif margin['time'] == user['time']['margin']:
            return
        else:
            user_margin = margin
            user_margin['time'] = user['time']['margin']

        user_margin['all_num'] = user['margin']['walletBalance']
        user_margin['order_cost'] = user['margin']['initMargin']
        user_margin['margin_cost'] = user['margin']['maintMargin']

        self.master.set_glob(self.MARGIN, user_margin)

    #初始化仓位
    def init_position(self, user, trade):
        position = self.master.get_glob(self.POSITION)
        user_position = position if position else {'time':0,'num':0,'lv':1,'price':0,'order_cost':0,'margin_cost':0,'buy_num':0,'sell_num':0,'buy_cost':0,'sell_cost':0}
        if 'position' in user and config.SYMBOL in user['position'] and user_position['time'] != user['time']['position']:
            position = user['position'][config.SYMBOL][0] if len(user['position'][config.SYMBOL]) > 0 else []
            user_position['time'] = user['time']['position']
            user_position['num'] = position['currentQty'] if 'currentQty' in position else 0
            user_position['lv'] = position['leverage'] if 'leverage' in position else 1
            user_position['price'] = position['avgEntryPrice'] if 'avgEntryPrice' in position else 0
            user_position['order_cost'] = position['initMargin'] if 'initMargin' in position else 0
            user_position['margin_cost'] = position['maintMargin'] if 'maintMargin' in position else 0
            user_position['buy_num'] = position['openOrderBuyQty'] if 'openOrderBuyQty' in position else 0
            user_position['sell_num'] = position['openOrderSellQty'] if 'openOrderSellQty' in position else 0
            user_position['buy_cost'] = position['openOrderBuyCost'] if 'openOrderBuyCost' in position else 0
            user_position['sell_cost'] = position['openOrderSellCost'] if 'openOrderSellCost' in position else 0

        if trade:
            if 'orderBook10' in trade and config.SYMBOL in trade['orderBook10']:
                user_position['buys'] = trade['orderBook10'][config.SYMBOL][0]['bids']
                user_position['sells'] = trade['orderBook10'][config.SYMBOL][0]['asks']
                user_position['last_buy'] = user_position['buys'][0][0]
                user_position['last_sell'] = user_position['sells'][0][0]
            if 'funding' in trade and config.SYMBOL in trade['funding']:
                user_position['now_free'] = trade['funding'][config.SYMBOL][0]['fundingRate']
                user_position['next_free'] = trade['funding'][config.SYMBOL][0]['fundingRateDaily']

        if user_position:
            self.master.set_glob(self.POSITION, user_position)

    #初始化订单
    def init_order(self,user):
        if 'order' not in user:
            return

        order = self.master.get_glob(self.ORDER)

        if order and order['time'] == user['time']['order']:
            return

        user_order = {'time': user['time']['order'], 'buy_num': 0, 'sell_num': 0, 'all':[]}
        user_order['new'] = order['new'] if order and 'new' in order else {}

        sign   = {'Buy': 0, 'Sell': 0}
        keys   = {'Buy': {}, 'Sell': {}}
        orders = {'Buy': [], 'Sell': []}

        if config.SYMBOL in user['order']:
            for order in user['order'][config.SYMBOL]:
                side = order['side']
                price = order['price'] if order['price'] else 0
                leavesQty = order['leavesQty'] if order['leavesQty'] else 0

                user_order['all'].append({'orderID':order['orderID'],'clOrdID':order['clOrdID'],'side':order['side'],'price':order['price'],'orderQty':order['orderQty'],'leavesQty':order['leavesQty'],'cumQty':order['cumQty'],})

                if side == 'Buy':
                    user_order['buy_num'] += leavesQty
                else:
                    user_order['sell_num'] += leavesQty

                if price not in keys[side]:
                    keys[side][price] = sign[side]
                    orders[side].append([price, leavesQty, [order['orderID']]])
                    sign[side] = sign[side] + 1
                else:
                    sp = keys[side][price]
                    orders[side][sp][1] = orders[side][sp][1] + leavesQty
                    orders[side][sp][2].append(order['orderID'])

            for d in orders:
                user_order[d] = [] if len(orders[d]) == 0 else [[k, orders[d][keys[d][k]][1], orders[d][keys[d][k]][2]] for k in sorted(keys[d].keys(), reverse=True if d == 'Buy' else False)]

        self.master.set_glob(self.ORDER,user_order)

    # 设置k线
    def init_kline(self, trade):
        kline = self.master.get_glob(self.KLINE)
        if not kline or 'tradeBin1h' not in trade or config.SYMBOL not in trade['tradeBin1h']:
            return False
        new_kline = {}
        for key,val in kline.items():
            if key not in trade or config.SYMBOL not in trade[key]:
                new_kline[key] = val
            elif val[-1]['timestamp'] == trade[key][config.SYMBOL][-1]['timestamp']:
                val[-1] = trade[key][config.SYMBOL][-1]
                new_kline[key] = val
            elif len(trade[key][config.SYMBOL]) >= self.kline_num:
                new_kline[key] = trade[key][config.SYMBOL]
            else:
                new_kline[key] = self.merge_kline(val,trade[key][config.SYMBOL])
        self.master.set_glob(self.KLINE,new_kline)

    # 合并k线
    def merge_kline(self, old_kline, new_kline):
        timestamp = new_kline[0]['timestamp']
        pre_kline = []
        for i in range(len(old_kline)):
            if timestamp == old_kline[i]['timestamp']:
                break
            else:
                pre_kline.append(old_kline[i])

        return pre_kline+new_kline

