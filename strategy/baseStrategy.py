# encoding: utf-8
from process import config
from decimal import Decimal

class baseStrategy(object):
    PRO_CNAME = 'strategy'
    MIN_NUM = 50
    MIN_PRICE = 0.5

    def __init__(self):
        self.symbol = config.SYMBOL
        self.tickLog = Decimal(str(self.MIN_PRICE)).as_tuple().exponent * -1
        self.s = {}

    def toNearest(self, num):
        tickDec = Decimal(str(self.MIN_PRICE))
        return float((Decimal(round(num / self.MIN_PRICE, 0)) * tickDec))