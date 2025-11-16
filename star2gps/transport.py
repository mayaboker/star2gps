import logging
from star2gps import SingletonMeta
import socket
import serial

log = logging.getLogger(__name__)




class SerialConnection:
    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.__ser = None

    def open(self):
        """Open the serial port."""
        if self.__ser is None:
            self.__ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            log.debug(f"Opened serial port {self.port} at {self.baudrate} baud")

    def close(self):
        """Close the serial port."""
        if self.__ser and self.__ser.is_open:
            self.__ser.close()
            log.debug(f"Closed serial port {self.port}")

    def write(self, data: bytes):
        """Write bytes to the serial port."""
        if not self.__ser or not self.__ser.is_open:
            raise RuntimeError("Serial port not open. Call open() first.")
        self.__ser.write(data)

    def __del__(self):
        """Cleanup on destruction."""
        self.close()


class Transport(metaclass=SingletonMeta):
    """
    publish payload via UDP
    """
    def __init__(self, address: str, port: int):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.address = address
        self.port = port
        log.info(f"UDP Transport initialized to send to {address}:{port}")

    #region public
    def send_gps(self, payload: bytes):
        try:
            self.sock.sendto(payload, (self.address, self.port))
            
        except Exception as e:
            log.exception("Failed to send UDP packet")

    def close(self):
        self.sock.close()
        log.info("UDP socket closed")

    #endregion

if __name__ == "__main__":
    serial_conn = SerialConnection(port="/dev/pts/13", baudrate=9600)
    serial_conn.open()
    serial_conn.write(b"Hello, Serial Port!")
    serial_conn.close()