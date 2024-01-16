from dataclasses import dataclass
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
import time

@dataclass
class ShunkeiDevice:
    hostname: str
    device_type: str
    ip_address: str

def find_vtx_tx_first(timeout: float = 5.0) -> ShunkeiDevice | None:

    class MyListener(ServiceListener):
        found_device: ShunkeiDevice = None

        def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            print(f"Service {name} updated")

        def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            print(f"Service {name} removed")

        def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            info = zc.get_service_info(type_, name)
            for address in info.addresses:
                ip_string = '.'.join(f'{c}' for c in address)
                self.found_device = ShunkeiDevice(
                    hostname=info.server,
                    device_type=info.type,
                    ip_address=ip_string
                )

    zeroconf = Zeroconf()
    listener = MyListener()
    browser = ServiceBrowser(zeroconf, "_shunkei_vtx_tx._tcp.local.", listener)

    started = time.time()
    try:
        while True:
            if listener.found_device is not None:
                return listener.found_device
            if time.time() - started > timeout:
                return None
            time.sleep(0.1)
    finally:
        zeroconf.close()

if __name__ == '__main__':
    device = find_vtx_tx_first(5)
    print(device.hostname, device.device_type, device.ip_address)


