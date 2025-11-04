import sys
import argparse
from mavlink import GPSReceiver
from storage import Storage
from transport import Transport
from dataclasses import dataclass
import signal
from star2gps import SingletonMeta
import logging
import struct

from  star2gps import DATA_FORMAT

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


@dataclass
class Options:
    gps: bool = True
    log: bool = True
    udp: bool = True
    dest_address: str = "127.0.0.1"
    dest_port: int = 5005

class Star2GPS(metaclass=SingletonMeta):
    def __init__(self):
        log.info("Starting Star2GPS...")
        self.mavlink_handler = None
        self.storage: Storage = None
        self.transport = None

    def _handle_gps_data(self, lat, lot, alt):
        log.info(f"GPS Data - Lat: {lat}, Lon: {lot}, Alt: {alt}")
        payload = struct.pack(DATA_FORMAT, float(lat), float(lot), float(alt))
        log.debug("Packed GPS payload: %s", payload.hex())
        if options.log:
            self.storage.write(payload)
        if options.udp:
            log.debug("Sending GPS data via UDP")
            self.transport.send_gps(payload)
        
    def run(self):
        if options.udp:
            self.transport = Transport(options.dest_address, options.dest_port)
        if options.log:
           self.storage = Storage()

        if options.gps:
            self.mavlink_handler = GPSReceiver()
            self.mavlink_handler.on_gps_data += self._handle_gps_data
            self.mavlink_handler.run()
            # exit immediately on Ctrl-C or termination
        signal.pause()

    def close(self):
        log.info("Shutting down Star2GPS...")
        if self.mavlink_handler:
            self.mavlink_handler.close()
        if self.transport:
            self.transport.close()
        if self.storage:
            self.storage.close()
        
def _handle_exit(signum, frame):
    start2gps.close()
    exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, _handle_exit)
    signal.signal(signal.SIGTERM, _handle_exit)
    parser = argparse.ArgumentParser(description="star2gps options")
    parser.add_argument('--gps', dest='gps', action='store_true', help='enable GPS output')
    parser.add_argument('--log', dest='log', action='store_true', help='enable logging')
    parser.add_argument('--udp', dest='udp', action='store_true', help='enable UDP output')
    parser.set_defaults(gps=True, log=True, udp=True)

    args = parser.parse_args()
    options = Options(
        args.gps,
        args.log,
        args.udp,
    )
    
    start2gps = Star2GPS()
    start2gps.run()