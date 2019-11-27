# encoding: utf-8
import sys
sys.path.append('..')
import time,logging
import talib
import pandas as pd
from strategy.baseStrategy import baseStrategy

class testStrategy(baseStrategy):
    def __init__(self):
        super().__init__()

        logging.info('strategy init')

        self.lines = ['tradeBin1d']
        self.sars = {}
        self.atrs = {}
        self.typprice = {}
        self.new_order = {}
        self.dateline = 0

    def init(self, margin, position, order, kline):
        self.margin = margin
        self.position = position
        self.order = order
        self.kline = kline

        # if not self.check_time():
        #     return

        # self.set_kline()
        # self.check_lines()
        # self.set_target()
        self.create_orders()

    def check_time(self):
        # 15分钟执行一次
        if 'tradeBin5m' in self.kline:
            timestamp = str(self.kline['tradeBin5m'][-1]['timestamp'])
        elif 'date' in self.kline:
            timestamp = str(self.kline['date'])
        else:
            return False
        dateline = time.mktime(time.strptime(timestamp.replace('T', ' ').replace('.000Z', ''), "%Y-%m-%d %H:%M:%S"))
        if self.dateline != dateline and dateline % 60 == 0:
            self.dateline = dateline
        else:
            return False

        return True

    def create_orders(self):
        self._lv()
        self._pos()

        self.sanity_check()
        self.set_orders()

    def get_order(self):
        return self.new_order if len(self.new_order) > 0 else []

    def set_kline(self):
        for keys, vals in self.kline.items():
            self.kline[keys] = pd.DataFrame(vals, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

    def check_lines(self):
        for i in self.lines:
            if i not in self.kline:
                raise Exception('kline {} is not exist'.format(i))

    def set_target(self):
        for i in self.lines:
            self.sars[i] = talib.SAREXT(self.kline[i]['high'], self.kline[i]['low'])
            # self.atrs[i] = talib.ATR(self.kline[i]['high'], self.kline[i]['low'], self.kline[i]['close'], 8)
            # self.typprice[i] = talib.TYPPRICE(self.kline[i]['high'], self.kline[i]['low'], self.kline[i]['close'])

    def _lv(self):
        if self.s and abs(self.s['all_num'] - self.margin['all_num']) < 100000: return

        self.s['all_num'] = self.margin['all_num']

        self.s['lv'] = 10     #杠杆倍数
        self.s['order_pairs'] = 3     #下单次数

        #以当前价维持价差
        self.s['maintain_spreads'] = True
        #维持美元单位
        self.s['dollar_base'] = False

        #最大订单数
        self.s['max_size'] = int((self.margin['all_num'] * (self.position['last_buy'] * (self.s['lv'] - 5)) / 100000000)/self.s['order_pairs'])*self.s['order_pairs']
        #最小订单数
        self.s['min_size'] = -self.s['max_size']

        #维持价差百分比
        self.s['interval'] = 0.012
        #第一仓位与当前价格的百分比
        self.s['min_spread'] = 0.0012
        #价格相似
        self.s['price_like'] = round(10/self.position['last_buy'], 3)
        #订单叠加数
        self.s['step_size'] = int((self.s['max_size']/self.s['order_pairs'])*((self.s['order_pairs']-1)/2/self.s['order_pairs']))
        #订单最小数
        self.s['start_size'] = int(self.s['max_size']/self.s['order_pairs'] - self.s['step_size']*(self.s['order_pairs']-1)/2)

        logging.info(self.s)

    def _pos(self):
        #现在仓位
        self.pos_num       = self.position['num']

    def sanity_check(self):
        self.get_ticker()
        if self.get_price_offset(-1) >= self.position['last_sell'] or self.get_price_offset(1) <= self.position['last_buy']:
            raise Exception("Sanity check failed, exchange data is inconsistent")

        # if self.long_position_limit_exceeded():
        #     logging.info("buy limit")
        #
        # if self.short_position_limit_exceeded():
        #     logging.info("sell limit")

    def get_ticker(self):
        self.start_position_buy = self.position['last_buy'] + self.MIN_PRICE
        self.start_position_sell = self.position['last_sell'] - self.MIN_PRICE

        if self.s['maintain_spreads']:
            if 'Buy' in self.order and len(self.order['Buy']) > 0 and  self.position['last_buy'] == self.order['Buy'][0][0]:
                self.start_position_buy = self.position['last_buy']
            if 'Sell' in self.order and len(self.order['Sell']) > 0 and self.position['last_sell'] == self.order['Sell'][0][0]:
                self.start_position_sell = self.position['last_sell']

        if self.start_position_buy * (1.00 + self.s['min_spread']) > self.start_position_sell:
            self.start_position_buy *= (1.00 - (self.s['min_spread'] / 2))
            self.start_position_sell *= (1.00 + (self.s['min_spread'] / 2))

    def short_position_limit_exceeded(self):
        return self.position['num'] <= self.s['min_size']

    def long_position_limit_exceeded(self):
        return self.position['num'] >= self.s['max_size']

    def set_orders(self):
        orders = self.place_orders()
        self.new_order = orders

    def place_orders(self):
        buy_orders = []
        sell_orders = []

        if self.position['num'] > 0:
            buy_num = self.position['num']
            sell_num = 0
        else:
            buy_num = 0
            sell_num = self.position['num']

        #reversed
        for i in range(1, self.s['order_pairs'] + 1):
            if not self.long_position_limit_exceeded():
                buy_order = self.prepare_order(-i)
                if buy_num >= buy_order['orderQty']:
                    buy_num -= buy_order['orderQty']
                else:
                    buy_order['orderQty'] = buy_order['orderQty'] - buy_num
                    buy_num = 0
                    if buy_order['orderQty'] < self.MIN_NUM:
                        continue
                    buy_orders.append(buy_order)

            if not self.short_position_limit_exceeded():
                sell_order = self.prepare_order(i)
                if sell_num <= -sell_order['orderQty']:
                    sell_num += sell_order['orderQty']
                else:
                    sell_order['orderQty'] = sell_order['orderQty']+sell_num
                    sell_num = 0
                    if sell_order['orderQty'] < self.MIN_NUM:
                        continue
                    sell_orders.append(sell_order)


        if self.s['dollar_base']:
            buy_orders = self.close_sell(buy_orders)

        return self.converge_orders(buy_orders, sell_orders)

    def close_sell(self, buy_orders):
        if not self.s['dollar_base']: return buy_orders

        if self.pos_num >= 0: return []

        new_buy = []
        buy_num = self.pos_num
        for order in buy_orders:
            if order['orderQty']+buy_num <=0:
                new_buy.append(order)
                buy_num = order['orderQty'] + buy_num
            else:
                order['orderQty'] = -buy_num
                new_buy.append(order)
                break
        return new_buy


    def converge_orders(self, buy_orders, sell_orders):
        new_order = {}
        up_order  = []
        add_order = []
        del_order = []
        buys_matched = 0
        sells_matched = 0

        for order in self.order['all']:
            try:
                if order['side'] == 'Buy':
                    desired_order = buy_orders[buys_matched]
                    buys_matched += 1
                else:
                    desired_order = sell_orders[sells_matched]
                    sells_matched += 1

                if desired_order['orderQty'] != order['leavesQty'] or (desired_order['price'] != order['price'] and abs((desired_order['price'] / order['price']) - 1) > self.s['price_like']):
                    up_order.append({'orderID': order['orderID'], 'orderQty': order['cumQty'] + desired_order['orderQty'],'price': desired_order['price'], 'side': order['side']})
            except IndexError:
                del_order.append(order)

        while buys_matched < len(buy_orders):
            add_order.append(buy_orders[buys_matched])
            buys_matched += 1

        while sells_matched < len(sell_orders):
            add_order.append(sell_orders[sells_matched])
            sells_matched += 1

        if len(up_order) > 0:
            new_order['up_order'] = up_order
        if len(add_order) > 0:
            new_order['add_order'] = add_order
        if len(del_order) > 0:
            new_order['del_order'] = del_order

        return new_order

    def prepare_order(self, index):
        quantity = self.s['start_size'] + ((abs(index) - 1) * self.s['step_size'])

        price = self.get_price_offset(index)

        return {'symbol': self.symbol,'price': price,'orderQty': quantity, 'side': "Buy" if index < 0 else "Sell"}

    def get_price_offset(self, index):
        """Given an index (1, -1, 2, -2, etc.) return the price for that side of the book.
           Negative is a buy, positive is a sell."""
        # Maintain existing spreads for max profit
        if self.s['maintain_spreads']:
            start_position = self.start_position_buy if index < 0 else self.start_position_sell
            # First positions (index 1, -1) should start right at start_position, others should branch from there
            index = index+1   if index < 0 else index - 1
        else:
            # Offset mode: ticker comes from a reference exchange and we define an offset.
            start_position = self.start_position_buy if index < 0 else self.start_position_sell

            # If we're attempting to sell, but our sell price is actually lower than the buy,
            # move over to the sell side.
            if index > 0 and start_position < self.start_position_buy:
                start_position = self.start_position_sell
            # Same for buys.
            if index < 0 and start_position > self.start_position_sell:
                start_position = self.start_position_buy

        return self.toNearest(start_position * (1 + self.s['interval']) ** index)

if __name__ == '__main__':
    test = testStrategy()