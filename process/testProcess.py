# encoding: utf-8
import time,logging
from process import config
from process.processInterface import processInterface

class testProcess(processInterface):
    PRO_CNAME = 'test'
    def init(self,master,user):
        self.master = master
        self.user = user
        self.master.set_pro_name(self.PRO_CNAME)
        while True:
            try:
                self.master.check_gid()
                time.sleep(5)
            except:
                self.master.sysError()