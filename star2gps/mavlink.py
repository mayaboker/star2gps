# 
# Read GPS data via MAVLink protocol
# 
from pymavlink import mavutil
import threading
import logging
from star2gps import Event
# Connect to the MAVLink stream (choose the right one for your setup)
# Examples:
# connection = mavutil.mavlink_connection('udp:127.0.0.1:14550')
# connection = mavutil.mavlink_connection('tcp:127.0.0.1:5760')
# connection = mavutil.mavlink_connection('/dev/ttyUSB0', baud=57600)

log = logging.getLogger(__name__)

class GPSReceiver:
    def __init__(self, connection_string="tcp:127.0.0.1:5760"):
        self.__open(connection_string)
        self.is_closing = False
        self.on_gps_data = Event()

    def __open(self, connection_string):
        log.info("Opening MAVLink connection...")
        try:
            self.master = mavutil.mavlink_connection(connection_string)
            self.request_gps_stream()
            self.master.wait_heartbeat()
            log.info("MAVLink heartbeat received.")
        except Exception as e:
            log.error("Failed to open MAVLink connection")
            raise e

    def request_gps_stream(self):
        # Request GPS data stream
        self.master.mav.request_data_stream_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_DATA_STREAM_ALL,
            5,   # rate in Hz
            1    # start streaming (1=on, 0=off)
        )

    def receive_gps_data(self):
        while True:
            # Wait for a GPS message
            msg = self.master.recv_match(type=['GPS_RAW_INT', 'GPS2_RAW'], blocking=True)
            if msg:
                gps = msg.to_dict()
                lat = gps['lat'] / 1e7
                lon = gps['lon'] / 1e7
                alt = gps['alt'] / 1000
                self.on_gps_data.fire(
                    lat,
                    lon,
                    alt
                )


            if self.is_closing:
                break
        self._close()

    def run(self):
        t = threading.Thread(target=self.receive_gps_data)
        t.start()


    def close(self):
        self.is_closing = True

    def _close(self):
        log.info("Closing MAVLink connection...")
        self.master.close()
        

if __name__ == "__main__":
    connection_string = "tcp:127.0.0.1:5760"
    mav = GPSReceiver(connection_string)
    mav.run()


