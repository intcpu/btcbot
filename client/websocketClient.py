# encoding: UTF-8

import sys
import json
import logging
import ssl
import traceback
from datetime import datetime
from threading import Lock, Thread
import websocket


class websocketClient(object):
    """
    Websocket API

    After creating the client object, use start() to run worker and ping threads.
    The worker thread connects websocket automatically.

    Use stop to stop threads and disconnect websocket before destroying the client
    object (especially when exiting the programme).

    Default serialization format is json.

    Callbacks to overrides:
    * unpack_data
    * on_connected
    * on_disconnected
    * on_packet
    * on_error

    After start() is called, the ping thread will ping server every 60 seconds.

    If you want to send anything other than JSON, override send_packet.
    """

    def __init__(self):
        """Constructor"""
        self.host = None

        self._ws_lock = Lock()
        self._ws = None

        self._worker_thread = None
        self._active = False

        self.proxy_host = None
        self.proxy_port = None
        self.ping_interval = 60     # seconds
        self.ping_timeout  = 5     # seconds

        # For debugging
        self._last_sent_text = None
        self._last_received_text = None

    def init(self, host: str, proxy_host: str = "", proxy_port: int = 0, ping_interval: int = 60,ping_timeout: int = 30):
        """
        :param ping_interval: unit: seconds, type: int
        """
        self.host = host
        self.ping_interval = ping_interval  # seconds
        self.ping_timeout  = ping_timeout  # seconds

        if proxy_host and proxy_port:
            self.proxy_host = proxy_host
            self.proxy_port = proxy_port



    def start(self):
        self._active = True
        self._worker_thread = Thread(target=self._run)
        self._worker_thread.start()

    def _run(self):
        try:
            self._connect()
        except:  # noqa
            et, ev, tb = sys.exc_info()
            self.on_error(et, ev, tb)
            self._reconnect()

    def _connect(self):
        #websocket开启日志跟踪
        # websocket.enableTrace(True)
        self._ws = websocket.WebSocketApp(self.host,
                                 on_message=self.__on_message,
                                 on_close=self.__on_close,
                                 on_open=self.__on_open,
                                 on_error=self.__on_error,
                                 keep_running=True,
                                 header=self.on_header())

        _kwargs = {'ping_interval':self.ping_interval,'ping_timeout':self.ping_timeout}

        if self.proxy_host and self.proxy_port:
            ssl_defaults = ssl.get_default_verify_paths()
            sslopt_ca_certs = {'ca_certs': ssl_defaults.cafile}
            _kwargs = {'ping_interval': self.ping_interval, 'ping_timeout': self.ping_timeout,'sslopt': sslopt_ca_certs}
            _kwargs['http_proxy_host'] = self.proxy_host
            _kwargs['http_proxy_port'] = self.proxy_port

        #daemon进程模式 程序执行完退出
        # self._ws.daemon = True
        self._ws.run_forever(**_kwargs)

        if not self._ws.sock or not self._ws.sock.connected:
            logging.error('Could not connect to WS! Exiting')


    #连接打开时
    def __on_open(self):
        '''Called when the WS opens.'''
        logging.info("Websocket Opened.  __on_open")
        self.on_connected()

    #链接关闭时
    def __on_close(self):
        '''Called on websocket close.'''
        logging.info('Websocket Closed. __on_close')
        self.on_disconnected()

    #报错时
    def __on_error(self, error):
        logging.info('Websocket Error start. __on_error')
        '''Called on fatal websocket errors. We exit on these.'''
        if self._active:
            logging.error("Error : %s" % error)
            #raise websocket.WebSocketException(error)
        et, ev, tb = sys.exc_info()
        self.on_error(et, ev, tb)

        logging.info('Websocket Error end. __on_error')
    #发送header头
    def on_header(self):
        return []

    #所有消息接收
    def __on_message(self, message):
        self._record_last_received_text(message)
        try:
            data = self.unpack_data(message)
        except ValueError as e:
            logging.warning("websocket unable to parse data: " + message)
            raise e

        self.on_packet(data)

    def stop(self):
        logging.info('stop')
        """
        Stop the client.

        This function cannot be called from worker thread or callback function.
        """
        self._active = False
        self._disconnect()

    def join(self):
        """
        Wait till all threads finish.
        """
        self._worker_thread.join()

    def send_packet(self, packet: dict):
        """
        Send a packet (dict data) to server

        override this if you want to send non-json packet
        """
        text = json.dumps(packet)
        self._record_last_sent_text(text)
        return self._send_text(text)

    def _send_text(self, text: str):
        """
        Send a text string to server.
        """
        ws = self._ws
        if ws:
            # ws.send(text, opcode=websocket.ABNF.OPCODE_TEXT)
            ws.send(text)

    def _send_binary(self, data: bytes):
        """
        Send bytes data to server.
        """
        ws = self._ws
        if ws:
            ws._send_binary(data)

    def _reconnect(self):
        """"""
        if self._active:
            self._disconnect()
            self._connect()

    def _disconnect(self):
        """
        """
        with self._ws_lock:
            if self._ws:
                self._ws.close()
                self._ws = None



    @staticmethod
    def unpack_data(data: str):
        """
        Default serialization format is json.

        override this method if you want to use other serialization format.
        """
        return json.loads(data)

    @staticmethod
    def on_connected():
        """
        Callback when websocket is connected successfully.
        """
        pass

    @staticmethod
    def on_disconnected():
        """
        Callback when websocket connection is lost.
        """
        pass

    @staticmethod
    def on_packet(packet: dict):
        """
        Callback when receiving data from server.
        """
        pass

    def on_error(self, exception_type: type, exception_value: Exception, tb):
        """
        Callback when exception raised.
        """
        logging.error(
            self.exception_detail(exception_type, exception_value, tb)
        )
        return sys.excepthook(exception_type, exception_value, tb)

    def exception_detail(
        self, exception_type: type, exception_value: Exception, tb
    ):
        """
        Print detailed exception information.
        """
        text = "[{}]: Unhandled WebSocket Error:{}\n".format(
            datetime.now().isoformat(), exception_type
        )
        text += "LastSentText:\n{}\n".format(self._last_sent_text)
        text += "LastReceivedText:\n{}\n".format(self._last_received_text)
        text += "Exception trace: \n"
        text += "".join(
            traceback.format_exception(exception_type, exception_value, tb)
        )
        return text

    def _record_last_sent_text(self, text: str):
        """
        Record last sent text for debug purpose.
        """
        self._last_sent_text = text[:1000]

    def _record_last_received_text(self, text: str):
        """
        Record last received text for debug purpose.
        """
        self._last_received_text = text[:1000]
