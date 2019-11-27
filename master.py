# encoding: utf-8
import os, sys, signal
import time, logging, traceback
import multiprocessing as mp
import importlib
from api.dingApi import dingApi
import setproctitle

class master():
    BOT_NAME = 'bitmex'
    PRO_CNAME = 'matser'
    def __init__(self):
        self.manager = None
        self._list = []
        #全局变量  一维字典
        self.glob = {}
        #局部变量 二维字典
        self.local = {}
        #进程信息
        self.process = {}
        self.dd = dingApi()
        self.time = int(time.time())

        self.process_paths  = {'process':['Process.py',None],'strategy':['Strategy.py','strategyProcess.py']}
        self.watched_mtimes = {}

    #run
    def run(self):
        self.set_pro_name(self.PRO_CNAME)
        self.set_mtimes()

        while True:
            self.check_mtimes()
            self.check_process()
            time.sleep(3)

    #启动消息进程
    def start_manager(self):
        if not self.manager:
            self.set_pro_name('manager')
            self.manager = mp.Manager()
            self._list = self.manager.list()
            self.glob = self.manager.dict()
            self.local = self.manager.dict()
            self.lock = self.manager.Lock()
            # self.queue = self.manager.Queue()


    # 关闭消息进程
    def stop_managet(self):
        if self.manager:
            self.manager.shutdown()

    #增加子进程
    def add_process(self, func=None, param=None, pname=None):
        try:
            if pname in self.process:
                raise Exception(str(os.getpid())+'>> process '+pname+' has existed')
            else:
                process = mp.Process(target=func, args=param, name='py-service-' + pname)
                # process.daemon = True
                process.start()
                self.local[pname] = self.manager.dict() if self.manager else {}
                self.process[pname] = {'target': func, 'args': param, 'process': process}
                self.ding(str(os.getpid())+'>> '+pname+' process is start')
        except:
            self.error_msg()

    #检查所有子进程
    def check_process(self):
        try:
            for p,pv in self.process.items():
                if 'process' in pv:
                    process = pv['process']
                else:
                    continue
                if process and process.is_alive() is not True:
                    # process.terminate()
                    process.kill()
                    process = None
                    logging.info(str(os.getpid())+ '>> '+p+' process is_alive: false')

                if process is None:
                    process = mp.Process(target=pv['target'], args=pv['args'], name='service-' + p)
                    process.start()
                    self.process[p] = {'target': pv['target'], 'args': pv['args'], 'process':process}
                    self.ding(str(os.getpid())+'>> '+p+' process is start')
        except:
            self.error_msg()

    #检查进程模块是否被修改
    def check_mtimes(self):
        is_reload = False
        for name, file in self.watched_mtimes.items():
            for class_name, model_name, model_path, model_mtime in file:
                if os.path.getmtime(model_path) > model_mtime:
                    logging.info('{} is change'.format(model_name))
                    importlib.reload(importlib.import_module(model_name))
                    class_name, model_name, model_path, model_mtime = self.watched_mtimes[name][0]
                    logging.info('{} is reload'.format(model_name))
                    model_obj = importlib.reload(importlib.import_module(model_name))
                    model_class = getattr(model_obj, class_name)
                    process_name = getattr(model_class, 'PRO_CNAME')
                    if process_name in self.process:
                        self.process[process_name]['target'] = model_class().init
                        self.process[process_name]['process'].kill()
                    is_reload = True
        if is_reload:
            self.set_mtimes()
    #设置修改时间
    def set_mtimes(self):
        self.watched_mtimes = {}
        base_dir = os.getcwd() + os.sep
        for su,fa in self.process_paths.items():
            path = base_dir + su
            files = os.listdir(path)
            for f in files:
                if fa[0] not in f: continue
                if fa[1]:
                    name = fa[1]
                    if name not in self.watched_mtimes: continue
                else:
                    name =  f
                    self.watched_mtimes[name] = []
                self.watched_mtimes[name].append([f[0:-3],'{}.{}'.format(su,f[0:-3]),path + os.sep + f,os.path.getmtime(path + os.sep + f)])

    #设置进程名字
    def set_pro_name(self, pro_name=''):
        pro_name = 'btcbot-{}-{}'.format(self.BOT_NAME, pro_name)
        setproctitle.setproctitle(pro_name)
        logging.info('{} process init'.format(pro_name))

    #检查主进程
    def check_gid(self):
        pid = os.getpid()
        gid = os.getpgid(pid)
        try:
            os.kill(gid, 0)
        except OSError:
            msg = str(os.getpid())+'>> gid:' + str(gid) + ' is killed, pid:' + str(pid) + ' will kill'
            self.ding(msg)
            self.stop_managet()
            os.kill(pid, signal.SIGKILL)
            return False
        else:
            return True

    #系统错误
    def sysError(self):
        t, v, tb = sys.exc_info()
        logging.error(str(os.getpid()) + '>> manager process ' + str(t))
        if t in [ConnectionRefusedError,EOFError,BrokenPipeError]:
            self.stop()
        elif t not in [KeyboardInterrupt]:
            self.error_msg(t, v, tb)
            self.kill_me()

    #进程自杀
    def kill_me(self):
        pid = os.getpid()
        self.ding(str(os.getpid())+'>> pid ' + str(pid)+' has be killed')
        os.kill(pid, signal.SIGKILL)

    #脚本自杀
    def stop(self):
        # python = sys.executable
        # os.execl(python, python, *sys.argv)
        self.ding(str(os.getpid())+'>> ------STOP-----')
        try:
            os.kill(os.getpgid(os.getpid()), signal.SIGKILL)
        except:
            self.sysError()

    #报错信息
    def error_msg(self,t=None, v=None, tb=None):
        if not t:
            t, v, tb = sys.exc_info()
        text = "".join(
            traceback.format_exception(t, v, tb)
        )
        self.ding(text)

    #设置全局变量
    def set_glob(self,key,val):
        try:
            # self.lock.acquire()
            if key not in self.glob:
                i = len(self._list)
                self._list.append(val)
                self.glob[key] = i
            else:
                i = self.glob[key]
                self._list[i] = val
            # self.lock.release()
        except:
            self.sysError()

    #带全局锁变量
    def lock_glob(self,key,val=None):
        try:
            self.lock.acquire()
            result = None
            if val is None:
                result = self.get_glob(key)
            else:
                self.set_glob(key,val)
                result = True
            self.lock.release()
            return result
        except:
            logging.info('lock_glob is lock')
            return None

    #获取全局变量
    def get_glob(self, key):
        try:
            if key not in self.glob:
                return None
            i = self.glob[key]
            return self._list[i]
        except:
            self.sysError()

    #删除全局变量
    def del_glob(self, key):
        if key not in self.glob:
            return False
        i = self.glob[key]
        self._list[i] = None
        return True

    #设置进程变量
    def set_local(self,pname,key,val):
        try:
            if pname not in self.local:
                return False
            if key not in self.local[pname]:
                i = len(self._list)
                self._list.append(val)
                self.local[pname][key] = i
            else:
                i = self.local[pname][key]
                self._list[i] = val
        except:
            self.sysError()

    #获取进程变量
    def get_local(self, pname, key):
        try:
            if pname not in self.local or key not in self.local[pname]:
                return None
            i = self.local[pname][key]
            return self._list[i]
        except:
            self.sysError()

    #删除进程变量
    def del_local(self, pname, key):
        if pname not in self.local or key not in self.local[pname]:
            return False
        i = self.local[pname][key]
        self._list[i] = None
        return True

    #钉钉消息
    def ding(self,data):
        logging.info(data)
        # self.dd.data(data) if isinstance(data,list) else self.dd.msg(data)