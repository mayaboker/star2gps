import logging
from star2gps import SingletonMeta
import socket


log = logging.getLogger(__name__)



class Transport(metaclass=SingletonMeta):
    def __init__(self, address: str, port: int):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.address = address
        self.port = port
        log.info(f"UDP Transport initialized to send to {address}:{port}")

    def send_gps(self, payload: bytes):
        try:
            self.sock.sendto(payload, (self.address, self.port))
            log.debug(f"Sent UDP packet to {self.address}:{self.port}")
        except Exception as e:
            log.exception("Failed to send UDP packet")

    def close(self):
        self.sock.close()
        log.info("UDP socket closed")

        