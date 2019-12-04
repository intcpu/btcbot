# btcbot
Quantitative robot for bitmex or other Exchange

#### start
`python3 setup.py`
`nohup python3 setup.py &`

#### view progress
`ps aux|grep btcbot`

#### kill
`ps aux|grep btcbot|awk '{print $2}'|xargs kill -9`

#### view log
`tail -f logs/$(date "+%Y%m%d").log`


------

# 功能使用
1. 在strategy中添加一个策略类,结果生成:add_order、up_order、del_order即可
2. 在strategyProcess中加载策略,获取add_order、up_order、del_order,投入bitmexRestProcess进程
3. bitmexRestProcess 接收到订单信息,下单

------

# 结构
* api 各网站request及websocket api调用
* backtest 回测文件,单独执行
* client 调用第三方服务端的客户端: redis、mongo、websocket、request
* data 历史数据
* logs 执行日志
* process 进程类,每个类会在独立的进程中执行
 >bitmexPrivateWsProcess.py  bitmex个人账户信息websocket推送<br>
 >bitmexPublicWsProcess.py bitmex公开信息信息websocket推送<br>
 >bitmexRestProcess.py bitmex 下单请求进程<br>
 >config.py bitmex配置信息<br>
 >processInterface.py 进程接口<br>
 >strategyProcess.py 策略进程  加载strategy目录下的策略类<br>
 >userProcess.py 用户信息进程  所有公开和私有在此进程中组合到manager进程<br>
* strategy 策略类,由strategyProcess加载
* master.py 启动加载manager进程,管理所有进程,自动重起、重载其他进程
* setup.py 主入口,主进程,被杀后,其他进程自杀(manager无法自杀)