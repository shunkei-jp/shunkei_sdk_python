from pathlib import Path
import subprocess
import sys
import threading

PROXY_PASS = Path(__file__).parent / "dc_t"

class WebRTCProxy:
    room_id: str
    process: subprocess.Popen = None
    thread: threading.Thread = None
    def __init__(self, room_id: str):
        self.room_id = room_id


    def start(self, room_id: str):
        self.process = subprocess.Popen(
            [str(PROXY_PASS), "--room-id", "elnath-geek@interbee-control-oinori", "--sig-url", "wss://ayame-labo.shiguredo.app/signaling", "--sig-key", "RHYG5I8VrUniNw8oBX5iQG9_t41OopwhKgYfCupT5v3dJUkf", "--port", "12334", "--no-bytes"],
            stdout=sys.stdout,
            stderr=sys.stdout,
        )

        def run():
            self.process.wait()
            rc = self.process.returncode
            if rc != 0:
                print(f"proxy exited with code {rc}", file=sys.stderr)
            self.process = None
        t = threading.Thread(target=run)
        t.start()

    def alive(self) -> bool:
        return self.process is not None

    def stop(self):
        if self.process is None:
            raise Exception("process is stopped when not running")
        self.process.terminate()
        self.process = None

    def __del__(self):
        if self.process is not None:
            self.stop()
