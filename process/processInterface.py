# encoding: utf-8
import abc
class processInterface(object):
    __metaclass__ = abc.ABCMeta

    PRO_CNAME = 'process'

    # 抽象方法
    @abc.abstractmethod
    def init(self, **kwargs): pass