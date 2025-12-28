#!/usr/bin/env python3
"""
ublox_to_pstm_nofixblock.py

F9P UBX in -> synthetic STA-like messages out
- Always prints to stdout
- Optionally writes the same output to a second serial port

NO passthrough of receiver NMEA.
Receiver GSA is parsed internally to extract PRNs.
"""

import argparse
import struct
import sys
from datetime import datetime, timezone
import serial
import time

# =========================
# NMEA helpers
# =========================

def nmea_checksum(core: str) -> str:
    x = 0
    for ch in core:
        x ^= ord(ch)
    return f"{x:02X}"

def nmea_sentence(core: str) -> str:
    return f"${core}*{nmea_checksum(core)}\r\n"

def itow_to_hhmmss_ms(itow_ms: int) -> str:
    total_ms = int(itow_ms) % (24 * 3600 * 1000)
    hh = total_ms // 3600000
    total_ms %= 3600000
    mm = total_ms // 60000
    total_ms %= 60000
    ss = total_ms // 1000
    ms = total_ms % 1000
    return f"{hh:02d}{mm:02d}{ss:02d}.{ms:03d}"

def deg_to_nmea_lat(lat_deg: float):
    hemi = 'N' if lat_deg >= 0 else 'S'
    lat = abs(lat_deg)
    d = int(lat)
    m = (lat - d) * 60.0
    return f"{d:02d}{m:08.5f}", hemi

def deg_to_nmea_lon(lon_deg: float):
    hemi = 'E' if lon_deg >= 0 else 'W'
    lon = abs(lon_deg)
    d = int(lon)
    m = (lon - d) * 60.0
    return f"{d:03d}{m:08.5f}", hemi

def hms_from_ymdhms(year, month, day, hour, minute, second, nano):
    ms = int(round(nano / 1e6))
    s = max(0, min(59, int(second)))
    return f"{hour:02d}{minute:02d}{s:02d}.{ms:03d}"

def compact_date(year, month, day):
    return f"{day:02d}{month:02d}{year:04d}"

def unix_ts(year, month, day, hour, minute, second):
    try:
        dt = datetime(year, month, day, hour, minute, int(second), tzinfo=timezone.utc)
        return int(dt.timestamp())
    except Exception:
        return 0

# =========================
# UBX parsing
# =========================

SYNC1, SYNC2 = 0xB5, 0x62
UBX_NAV_PVT = (0x01, 0x07)
UBX_NAV_DOP = (0x01, 0x04)
UBX_TIM_TP  = (0x0D, 0x01)

def ubx_checksum(data: bytes):
    a = 0
    b = 0
    for v in data:
        a = (a + v) & 0xFF
        b = (b + a) & 0xFF
    return a, b

def read_ubx_or_byte(ser: serial.Serial):
    b = ser.read(1)
    if not b:
        return None, None, None
    if b[0] != SYNC1:
        return None, None, b
    b2 = ser.read(1)
    if not b2 or b2[0] != SYNC2:
        return None, None, b + b2

    hdr = ser.read(4)
    ubx_class, ubx_id, length = struct.unpack('<BBH', hdr)
    payload = ser.read(length)
    ck = ser.read(2)

    calc_a, calc_b = ubx_checksum(bytes([ubx_class, ubx_id]) + struct.pack('<H', length) + payload)
    if ck[0] != calc_a or ck[1] != calc_b:
        return None, None, None

    return ubx_class, ubx_id, payload

# =========================
# Caches
# =========================

class DOPCache:
    def __init__(self):
        self.pdop = self.hdop = self.vdop = None
    def update(self, p):
        if len(p) < 18:
            return
        _, _, pd, _, vd, hd, _, _ = struct.unpack('<IHHHHHHH', p[:18])
        self.pdop = pd / 100.0
        self.hdop = hd / 100.0
        self.vdop = vd / 100.0

class PPSCache:
    def __init__(self):
        self.width = 0.5
        self.delay_ns = 18
    def update(self, p):
        if len(p) >= 12:
            _, _, qErr = struct.unpack_from('<I i i', p, 0)
            self.delay_ns = abs(qErr)

class LastFix:
    def __init__(self):
        self.have = False
        self.lat = self.lon = self.alt = 0.0

class GSACache:
    def __init__(self):
        self.prns = []
        self.fix_mode = "1"
    def update(self, s):
        try:
            core = s[1:].split('*')[0]
            f = core.split(',')
            self.fix_mode = f[2]
            self.prns = [x for x in f[3:15] if x]
        except:
            pass

# =========================
# Constants
# =========================

NOFIX_DATE = "03092017"
NOFIX_UNIX = 1188432024
LEAP = 18

# =========================
# Builders
# =========================

def GNGSA_nofix():
    l1 = nmea_sentence("GNGSA,A,1," + ","*11 + ",99.0,99.0,99.0")
    l3 = nmea_sentence("GNGSA,A,1," + ","*7 + "$," + ","*3 + ",99.0,99.0,99.0")
    return l1 + l1 + l3

def GNGSA_fix(gsa, dop):
    prns = gsa.prns[:12] + [""] * (12 - len(gsa.prns))
    pd = dop.pdop if dop.pdop else 99.0
    hd = dop.hdop if dop.hdop else 99.0
    vd = dop.vdop if dop.vdop else 99.0
    core = "GNGSA,A,3," + ",".join(prns) + f",{pd:.1f},{hd:.1f},{vd:.1f}"
    s = nmea_sentence(core)
    return s * 3

def PSTMPPSDATA(pps, fix):
    core = (
        f"PSTMPPSDATA,1,{1 if fix else 0},{1 if fix else 0},0,1,{1 if fix else 0},"
        f"{pps.width:.6f},0,633,420,420,633,0,0,0,0,0,42,1,0,"
        f"{pps.delay_ns if fix else 18},0,0,0,1.092e-08,65473679.79,47999996.76,4"
    )
    return nmea_sentence(core)

def PSTMPV(p, dop, fix, last):
    itow = struct.unpack_from('<I', p, 0)[0]
    t = itow_to_hhmmss_ms(itow)

    lat = struct.unpack_from('<i', p, 28)[0] / 1e7
    lon = struct.unpack_from('<i', p, 24)[0] / 1e7
    alt = struct.unpack_from('<i', p, 36)[0] / 1000.0

    if not fix and last.have:
        lat, lon, alt = last.lat, last.lon, last.alt

    la, lh = deg_to_nmea_lat(lat)
    lo, loh = deg_to_nmea_lon(lon)

    if not fix:
        core = f"PSTMPV,{t},{la},{lh},{lo},{loh},{alt:.2f},M," + ",".join(["0.0"]*13)
    else:
        core = f"PSTMPV,{t},{la},{lh},{lo},{loh},{alt:.2f},M," + ",".join(["0.0"]*13)

    return nmea_sentence(core)

def PSTMPVRAW(p, fix):
    t = itow_to_hhmmss_ms(struct.unpack_from('<I', p, 0)[0])
    if not fix:
        core = f"PSTMPVRAW,{t},9000.00000,N,00000.00000,E,0,00,0.0,-6356752.31,M,0.0,M,nan,nan,nan"
    else:
        lat = struct.unpack_from('<i', p, 28)[0] / 1e7
        lon = struct.unpack_from('<i', p, 24)[0] / 1e7
        alt = struct.unpack_from('<i', p, 32)[0] / 1000.0
        la, lh = deg_to_nmea_lat(lat)
        lo, loh = deg_to_nmea_lon(lon)
        core = f"PSTMPVRAW,{t},{la},{lh},{lo},{loh},1,00,0.0,{alt:.2f},M,0.0,M,nan,nan,nan"
    return nmea_sentence(core)

def PSTMUTC(p, fix):
    itow = struct.unpack_from('<I', p, 0)[0]
    t = itow_to_hhmmss_ms(itow)
    if not fix:
        core = f"PSTMUTC,{t},{NOFIX_DATE},{NOFIX_UNIX},{LEAP},1,00,1,04,0"
    else:
        y = struct.unpack_from('<H', p, 4)[0]
        m, d, h, mi, s = p[6], p[7], p[8], p[9], p[10]
        n = struct.unpack_from('<i', p, 16)[0]
        core = f"PSTMUTC,{hms_from_ymdhms(y,m,d,h,mi,s,n)},{compact_date(y,m,d)},{unix_ts(y,m,d,h,mi,s)},{LEAP},1,00,1,04,0"
    return nmea_sentence(core)

def PSTMCPU():
    return nmea_sentence("PSTMCPU,11.82,-1,196")

# =========================
# Main
# =========================

def run(port, baud, outport, outbaud):
    ser = serial.Serial(port, baud, timeout=0.1)
    outser = serial.Serial(outport, outbaud, timeout=0.1) if outport else None

    def emit(s):
        sys.stdout.write(s)
        sys.stdout.flush()
        if not outser:
            return

        # Send line-by-line (keeps \r\n), with pacing so ESP/UART can't be overrun
        for line in s.splitlines(True):  # True keeps line endings
            if not line:
                continue
            b = line.encode("ascii", errors="ignore")
            outser.write(b)
            outser.flush()

            # At 115200 bps: ~10 bits/byte => seconds ≈ len(bytes)*10/baud
            time.sleep(len(b) * 10.0 / outbaud)

            # Extra safety: if OS buffer piles up, wait a bit
            while getattr(outser, "out_waiting", 0) > 2048:
                time.sleep(0.002)

    dop = DOPCache()
    latest_gga = None  # last receiver-provided GGA sentence (passthrough)

    pps = PPSCache()
    last = LastFix()
    gsa = GSACache()
    buf = bytearray()

    while True:
        cls, mid, payload = read_ubx_or_byte(ser)

        if cls is None and payload:
            buf.extend(payload)
            while b'\n' in buf:
                line, _, buf = buf.partition(b'\n')
                # Keep original content (minus trailing \r), preserve checksum as sent by receiver
                s = line.decode(errors="ignore").rstrip('\r')
                if not s:
                    continue
                if s.startswith("$"):
                    # Cache receiver GSA for PRN extraction
                    if "GSA" in s:
                        gsa.update(s)
                    # Cache latest receiver GGA for passthrough (accept GP or GN talker)
                    if "GGA" in s:
                        latest_gga = s + "\r\n"
            continue

        if (cls, mid) == UBX_NAV_DOP:
            dop.update(payload)
        elif (cls, mid) == UBX_TIM_TP:
            pps.update(payload)
        elif (cls, mid) == UBX_NAV_PVT:
            fix = payload[20] >= 2 and (payload[21] & 1)
            if fix:
                last.have = True
                last.lat = struct.unpack_from('<i', payload, 28)[0] / 1e7
                last.lon = struct.unpack_from('<i', payload, 24)[0] / 1e7
                last.alt = struct.unpack_from('<i', payload, 36)[0] / 1000.0

            if latest_gga:
                emit(latest_gga)
                emit(GNGSA_fix(gsa, dop) if fix else GNGSA_nofix())
                emit(PSTMPPSDATA(pps, fix))
                emit(PSTMPV(payload, dop, fix, last))
                emit(PSTMPVRAW(payload, fix))
                emit(PSTMUTC(payload, fix))
                emit(PSTMCPU())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True)
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--outport", help="Optional output serial port")
    ap.add_argument("--outbaud", type=int, default=115200)
    args = ap.parse_args()

    run(args.port, args.baud, args.outport, args.outbaud)
