# encoding: UTF-8

import json
import logging
import requests

########################################################################
class dingApi ():
    BASE_API_URL = 'https://oapi.dingtalk.com/robot/send?access_token='
    #钉钉token
    DEFAULT_TOKEN = ''

    JSON_HEADER = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'Content-Type': 'application/json;charset=utf-8'
    }
    def __init__(self,token=None):
        if token != None:
            self.BASE_API_URL = self.BASE_API_URL + token
        else:
            self.BASE_API_URL = self.BASE_API_URL + self.DEFAULT_TOKEN

    def msg(self, content, atAll=True):
        if not content or not self.DEFAULT_TOKEN: return

        text = {'msgtype': 'text', 'text': {'content':content}, 'at': {'isAtAll':atAll}}
        text = json.dumps(text)
        response = requests.post(self.BASE_API_URL, data=text, headers=self.JSON_HEADER)
        
        self._response(response)

    def data(self, content, atAll=True):
        if not content or not self.DEFAULT_TOKEN: return

        title = content.get('title', '!!!警告!!!')
        msg_str = "# "+title+"\r\n------"
        for msg in content:
            if msg == 'title':
                continue
            msg_str = msg_str+"\r\n#### "+str(msg)+" : "+str(content[msg])

        text = {'msgtype':'markdown', 'markdown': {'title': title, 'text': msg_str}, 'at': {'isAtAll': atAll}}
        text = json.dumps(text)
        response = requests.post(self.BASE_API_URL, data=text, headers=self.JSON_HEADER)
        
        self._response(response)

    def _response(self,response):
        if response.status_code == 200:
            try:
                text = json.loads(response.text)
                if text.get('errmsg') != 'ok':
                    logging.error('DingApi send failed: '+text['errmsg'])
            except:
                logging.error('DingApi is fail')
        else:
            logging.error('DingApi error status_code: '+str(response.status_code))

if __name__ == '__main__':
    ding = dingApi()
    ding.msg('操作失败')
    ding.data({
    "msg": "操作失败"
    })

