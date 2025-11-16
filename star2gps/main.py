import sys
import argparse
from mavlink import GPSReceiver
from storage import Storage
from transport import Transport, SerialConnection

from nmea import GPGGA
from dataclasses import dataclass
import signal
from star2gps import SingletonMeta
import logging
import nmea

from  star2gps import DATA_FORMAT

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


@dataclass
class Options:
    gps: bool = True
    log: bool = True
    baudrate: int = 9600
    port: str = "/dev/pts/13"
    
class Star2GPS(metaclass=SingletonMeta):
    """
    Main application class for Star2GPS.
    """
    def __init__(self):
        log.info("Starting Star2GPS...")
        self.mavlink_handler = None
        self.storage: Storage = None
        self.transport = None

    #region private
    def _handle_gps_data(self, lat, lon, alt, sats, hdop, fix_quality):
        """Handle incoming GPS from backend.
        serialize and send via UDP and/or log to file.
        """
        log.info(f"GPS Data - Lat: {lat}, Lon: {lon}, Alt: {alt}")
        payload = nmea.GPGGA(lat=lat, lon=lon, alt=alt, sats=sats, hdop=hdop, fix_quality=fix_quality).to_nmea().encode('ascii') + b'\r\n'
        log.debug("Packed GPS payload: %s", payload.hex())
        if options.log:
            self.storage.write(payload)
        
        self.transport.write(payload)
    #endregion

    # region public
    def run(self):
        try:
            
            # self.transport = Transport(options.dest_address, options.dest_port)
            self.transport = SerialConnection(port=options.port, baudrate=options.baudrate)
            self.transport.open()

            if options.log:
                self.storage = Storage()

            if options.gps:
                self.mavlink_handler = GPSReceiver()
                self.mavlink_handler.on_gps_data += self._handle_gps_data
                self.mavlink_handler.run()
            else:
                # TODO: implement 
                log.info("TODO: firefox ")
                
        except Exception as e:  
            log.error("Fail to start")
            self.close()
            sys.exit(1)
        finally:
            pass
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
        
    #endregion

# region main
def _handle_exit(signum, frame):
    """
    Handle exit signals to gracefully shut down the application.
    """
    start2gps.close()
    exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, _handle_exit)
    signal.signal(signal.SIGTERM, _handle_exit)
    parser = argparse.ArgumentParser(description="star2gps options")
    parser.add_argument('--gps', dest='gps', action='store_true', help='enable GPS output')
    parser.add_argument('--log', dest='log', action='store_true', help='enable logging')
    parser.add_argument('--baudrate', type=int, default=9600, help='serial boundrate')
    parser.add_argument('--port', type=str, default="/dev/pts/13", help='serial destination port')


    args = parser.parse_args()
    options = Options(
        args.gps,
        args.log,
        args.baudrate,
        args.port
    )
    
    start2gps = Star2GPS()
    start2gps.run()
# endregion