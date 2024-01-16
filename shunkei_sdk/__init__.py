from __future__ import annotations
import socket
import time

from .webrtc import WebRTCProxy
from .find_shunkei import find_vtx_tx_first

DEFAULT_PORT = 12334

# TODO: handle iroriona error

class FindShunkeiError(Exception):
    pass

class ShunkeiVTX:
    _socket: socket.socket
    _webRTCProxy: WebRTCProxy = None
    _host: str = None
    _port: int = None

    @classmethod
    def connect_via_ip(cls, host: str, port: int) -> ShunkeiVTX:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect((host, port))
        sock.setblocking(False)

        insatance = cls()
        insatance._socket = sock
        insatance._host = host
        insatance._port = port

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

    def read(self, size: int) -> bytes:
        if self._webRTCProxy is not None and not self._webRTCProxy.alive():
            raise Exception("webrtc proxy is stopped")
        try:
            return self._socket.recv(size)
        except BlockingIOError:
            return None

    def write(self, data: bytes):
        if self._webRTCProxy is not None and not self._webRTCProxy.alive():
            raise Exception("webrtc proxy is stopped")
        self._socket.send(data)

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    def close(self):
        self._socket.close()
        if self._webRTCProxy is not None:
            self._webRTCProxy.stop()

