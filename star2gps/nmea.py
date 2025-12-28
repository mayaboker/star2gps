
import time
from typing import Protocol, Tuple
from typing import List, Optional
from dataclasses import dataclass, field


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
class PSTMPV(NMEASentence):
    lat: float
    lon: float
    alt: float

    def _deg_to_nmea(self, value: float, is_lat: bool) -> Tuple[str, str]:
        """Convert decimal degrees to NMEA degrees/minutes format."""
        deg = int(abs(value))
        minutes = (abs(value) - deg) * 60
        direction = ("N" if value >= 0 else "S") if is_lat else ("E" if value >= 0 else "W")
        if is_lat:
            return f"{deg:02d}{minutes:07.4f}", direction
        else:
            return f"{deg:03d}{minutes:07.4f}", direction
        
    def to_nmea(self) -> str:       
        lat_str, lat_dir = self._deg_to_nmea(self.lat, True)
        lon_str, lon_dir = self._deg_to_nmea(self.lon, False)

        # Assemble the data fields
        data = f"PSTMPV,{lat_str},{lat_dir},{lon_str},{lon_dir},{self.alt:.1f}"
        data += "M," + ",".join(["0.0"]*13)
        checksum = self._checksum(data)
        return f"${data}*{checksum}"

@dataclass
class GNGSA(NMEASentence):
    """
    The
    GNGSA (GNSS DOP and Active Satellites) command is an NMEA 0183 sentence that provides detailed information 
    about the GNSS receiver's operating mode, the satellites used for the current position fix, 
    and Dilution of Precision (DOP) values for combined constellations 
    (such as GPS, GLONASS, Galileo, and BeiDou).


    $GNGSA,<mode1>,<mode2>,<sat1>,...,<sat12>,<PDOP>,<HDOP>,<VDOP>*<CS>
    """
    # Field 1: Mode 1 (selection mode)
    # "M" = manual, "A" = automatic
    mode1: str = "A"

    # Field 2: Mode 2 (fix type)
    # "1" = no fix, "2" = 2D, "3" = 3D
    mode2: str = "1"

    # Fields 3..14: up to 12 satellite IDs used for the solution
    # Use None/"" for empty slots when serializing
    # NMEA is "12 separate fields", so keep length exactly 12 in serialization.
    sv: List[Optional[int]] = field(default_factory=lambda: [None] * 12)

    # Fields 15..17: Dilution of precision
    pdop: Optional[float] = None
    hdop: Optional[float] = None
    vdop: Optional[float] = None

    def to_nmea(self) -> str:
        # Ensure exactly 12 satellite slots
        sv = (self.sv or [])[:12]
        sv += [None] * (12 - len(sv))

        # SV fields: 2-digit for GPS PRN is common, but receivers vary.
        # NMEA allows variable width; empty field when None.
        sv_fields = ",".join(f"{prn:02d}" if prn is not None else "" for prn in sv)

        # DOP fields: empty if None, otherwise formatted (commonly 1 decimal)
        pdop_str = f"{self.pdop:.1f}" if self.pdop is not None else ""
        hdop_str = f"{self.hdop:.1f}" if self.hdop is not None else ""
        vdop_str = f"{self.vdop:.1f}" if self.vdop is not None else ""

        # Assemble (no leading '$', no '*CS' yet), just like your GGA code
        data = (
            f"GNGSA,"
            f"{self.mode1},{self.mode2},"
            f"{sv_fields},"
            f"{pdop_str},{hdop_str},{vdop_str}"
        )

        checksum = self._checksum(data)
        return f"${data}*{checksum}"

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
        data = f"GPGGA,{utc_time},{lat_str},{lat_dir},{lon_str},{lon_dir}," \
               f"{self.fix_quality},{self.sats:02d},{self.hdop:.1f},{self.alt:.1f},M,{self.geoid_sep:.1f},M,,"

        checksum = self._checksum(data)
        return f"${data}*{checksum}"


if __name__ == "__main__":
    gga = GPGGA(lat=37.7749, lon=-122.4194, alt=15.0)
    print(gga.to_nmea())

    gsa = GNGSA(
        mode1="A",
        mode2="3",
        sv=[3, 7, 12, 19, 22, 28],
        pdop=1.5,
        hdop=0.9,
        vdop=1.2
    )
    print(gsa.to_nmea())

    pstmpv = PSTMPV(lat=37.7749, lon=-122.4194, alt=15.0)
    print(pstmpv.to_nmea())

