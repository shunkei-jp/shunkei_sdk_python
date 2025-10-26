from __future__ import annotations

import socket
import time
import queue
import threading
import datetime
import dataclasses

import requests
from requests.auth import HTTPBasicAuth

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

@dataclasses.dataclass(frozen=True)
class ShunkeiVTXVersion:
    software: str | None = None
    hardware: str | None = None
    image: str | None = None

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

    _username: str | None = None
    _password: str | None = None
    _version: ShunkeiVTXVersion | None = None

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

    def authorize(self, username, password):
        """
        Authorize for API Request
        """
        res = requests.get(f"http://{self.host}", auth=HTTPBasicAuth(username, password))
        res.raise_for_status()

        self._username = username
        self._password = password

    def _fetch_vtx_version(self):
        res = requests.get(
            f"http://{self.host}/api/version",
            auth=HTTPBasicAuth(self._username, self._password)
        )
        if res.status_code == 404:
            return ShunkeiVTXVersion()
        res.raise_for_status()
        software_version = res.json().get("software")
        hardware_version = res.json().get("hardware")
        image_version = res.json().get("image")
        return ShunkeiVTXVersion(
            software=software_version,
            hardware=hardware_version,
            image=image_version,
        )


    def get_version(self) -> ShunkeiVTXVersion:
        """
        Get version of Shunkei VTX
        """
        if self._version is not None:
            return self._version

        self._version = self._fetch_vtx_version()
        return self._version

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
            try:
                buf = self._socket.recv(1024)
            except OSError:
                break
            if not buf:
                continue
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
            try:
                self._socket.send(bytes([PACKET_TYPE_ECHO_REQUEST]) + start.to_bytes(16, "little"))
            except OSError:
                break
            time.sleep(1)

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    def close(self):
        self._alive = False

        sock = getattr(self, "_socket", None)
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
            self._socket = None

        if self._recv_thread:
            self._recv_thread.join()
            self._recv_thread = None
        if self._control_rtt_thread:
            self._control_rtt_thread.join()
            self._control_rtt_thread = None

        if self._webRTCProxy is not None:
            self._webRTCProxy.stop()
            self._webRTCProxy = None
