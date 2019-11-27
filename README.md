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
