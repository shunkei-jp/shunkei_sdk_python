from __future__ import annotations
import socket
import time
import queue
import threading
import datetime

from .webrtc import WebRTCProxy
from .find_shunkei import find_vtx_tx_first

DEFAULT_PORT = 12334

PACKET_TYPE_ECHO_REQUEST = 0
PACKET_TYPE_ECHO_RESPONSE = 1
PACKET_TYPE_UART = 128

# TODO: handle iroriona error

def get_timestamp_us() -> int:
    return int(datetime.datetime.now().timestamp() * 1e6)
class FindShunkeiError(Exception):
    pass

class ShunkeiVTX:
    _socket: socket.socket
    _webRTCProxy: WebRTCProxy = None
    _host: str = None
    _port: int = None

    _control_rtt: int | None = None
    _control_rtt_last: datetime.datetime | None = None

    _recv_thread = None
    _control_rtt_thread = None
    _alive: bool = True
    _uart_queue: queue.Queue = queue.Queue()

    @classmethod
    def connect_via_ip(cls, host: str, port: int) -> ShunkeiVTX:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect((host, port))

        insatance = cls()
        insatance._socket = sock
        insatance._host = host
        insatance._port = port

        insatance._recv_thread = threading.Thread(target=insatance._recv_thread_handler)
        insatance._recv_thread.daemon = True
        insatance._recv_thread.start()
        insatance._control_rtt_thread = threading.Thread(target=insatance._rtt_thread_handler)
        insatance._control_rtt_thread.daemon = True
        insatance._control_rtt_thread.start()

        return insatance

    @classmethod
    def auto_connect(cls) -> ShunkeiVTX:
        device = find_vtx_tx_first(5)
        if device is None:
            raise FindShunkeiError("device not found")
        host = device.ip_address
        port = DEFAULT_PORT
        print(f"device found: {host}")

        return cls.connect_via_ip(host, port)

    @classmethod
    def connect_via_webrtc(cls, room_id: str) -> ShunkeiVTX:
        # TODO: specify sig-server
        webrtc_proxy = WebRTCProxy(room_id)
        webrtc_proxy.start(room_id)
        time.sleep(1)

        instance = cls.connect_via_ip("127.0.0.1", DEFAULT_PORT)
        instance._webRTCProxy = webrtc_proxy

        return instance

    def uart_read(self, _) -> bytes:
        if self._uart_queue.empty():
            return None
        return self._uart_queue.get()

    def uart_write(self, data: bytes):
        if self._webRTCProxy is not None and not self._webRTCProxy.alive():
            raise Exception("webrtc proxy is stopped")
        self._socket.send(bytes([PACKET_TYPE_UART]) + data)

    @property
    def control_rtt_us(self) -> int | None:
        """
        return the rtt of control signal(UART) in micro seconds
        """
        return self._control_rtt

    @property
    def control_rtt_last(self) -> datetime.datetime | None:
        """
        return the time when the last control rtt was measured
        """
        return self._control_rtt_last

    def _recv_thread_handler(self):
        while self._alive:
            buf = self._socket.recv(1024)
            if buf[0] == PACKET_TYPE_UART:
                self._uart_queue.put(buf[1:])
            if buf[0] == PACKET_TYPE_ECHO_RESPONSE:
                start = int.from_bytes(buf[1:], "little")
                now = get_timestamp_us()
                self._control_rtt = now - start
                self._control_rtt_last = datetime.datetime.now()

    def _rtt_thread_handler(self):
        while self._alive:
            start = get_timestamp_us()
            self._socket.send(bytes([PACKET_TYPE_ECHO_REQUEST]) + start.to_bytes(16, "little"))
            time.sleep(1)

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    def close(self):
        self._alive = False
        if self._recv_thread:
            self._recv_thread.join()
        if self._control_rtt_thread:
            self._control_rtt_thread.join()

        self._socket.close()

        if self._webRTCProxy is not None:
            self._webRTCProxy.stop()

