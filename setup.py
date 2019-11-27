# encoding: utf-8
import time
import logging
from master import master
from process.bitmexPublicWsProcess import bitmexPublicWsProcess
from process.bitmexPrivateWsProcess import bitmexPrivateWsProcess
from process.strategyProcess import strategyProcess
from process.bitmexRestProcess import bitmexRestProcess
from process.userProcess import userProcess

logging.basicConfig(
    filename="./logs/" + time.strftime("%Y%m%d") + '.log',
    filemode="a",
    format="%(asctime)s %(name)s:%(levelname)s:%(message)s",
    level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S"
)

mat = master()
mat.start_manager()

user = userProcess()
mat.add_process(user.init, (mat,), user.PRO_CNAME)

pub_ws = bitmexPublicWsProcess()
mat.add_process(pub_ws.init, (mat, user,), pub_ws.PRO_CNAME)

pri_ws = bitmexPrivateWsProcess()
mat.add_process(pri_ws.init, (mat, user,), pri_ws.PRO_CNAME)

rest = bitmexRestProcess()
mat.add_process(rest.init, (mat, user,), rest.PRO_CNAME)

sp = strategyProcess()
mat.add_process(sp.init, (mat, user,), sp.PRO_CNAME)

mat.run()

# tail -f logs/$(date "+%Y%m%d").log
# python3 setup.py
# nohup python3 setup.py &
# ps aux|grep btcbot
# ps aux|grep btcbot|awk '{print $2}'|xargs kill -9