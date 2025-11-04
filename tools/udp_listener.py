
import socket
import struct
from  star2gps import DATA_FORMAT

def udp_gps_listener():
    record_struct = struct.Struct(DATA_FORMAT)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', 5005))
    while True:
        data, addr = sock.recvfrom(record_struct.size)
        lat, lon, alt = record_struct.unpack(data)
        print(f"Lat={lat}, Lon={lon}, Alt={alt}")
        # print("Received message:", data, "from", addr)

if __name__ == "__main__":
    udp_gps_listener()