
import time
from typing import Protocol, Tuple
from dataclasses import dataclass

TALKER = "GP"

class NMEASentence(Protocol):
    def to_nmea(self) -> str:
        ...

    def _checksum(self, sentence: str) -> str:
        """Compute NMEA XOR checksum."""
        csum = 0
        for ch in sentence:
            csum ^= ord(ch)
        return f"{csum:02X}"

@dataclass
class GPGGA(NMEASentence):
    lat: float
    lon: float
    alt: float = 0.0
    fix_quality: int = 1
    sats: int=8
    hdop: float=0.9
    fix_quality: int = 1    
    geoid_sep: float=0.0


    def _deg_to_nmea(self, value: float, is_lat: bool) -> Tuple[str, str]:
        """Convert decimal degrees to NMEA degrees/minutes format."""
        deg = int(abs(value))
        minutes = (abs(value) - deg) * 60
        direction = ("N" if value >= 0 else "S") if is_lat else ("E" if value >= 0 else "W")
        if is_lat:
            return f"{deg:02d}{minutes:07.4f}", direction
        else:
            return f"{deg:03d}{minutes:07.4f}", direction

    def to_nmea(self, ):
        """Generate a GPGGA NMEA sentence."""
        utc_time = time.strftime("%H%M%S.00", time.gmtime()) # TODO: verify synchronized time
        lat_str, lat_dir = self._deg_to_nmea(self.lat, True)
        lon_str, lon_dir = self._deg_to_nmea(self.lon, False)

        # Assemble the data fields
        data = f"{TALKER}GGA,{utc_time},{lat_str},{lat_dir},{lon_str},{lon_dir}," \
               f"{self.fix_quality},{self.sats:02d},{self.hdop:.1f},{self.alt:.1f},M,{self.geoid_sep:.1f},M,,"

        checksum = self._checksum(data)
        return f"${data}*{checksum}"


if __name__ == "__main__":
    gga = GPGGA(lat=37.7749, lon=-122.4194, alt=15.0)
    print(gga.to_nmea())