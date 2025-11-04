import logging
import struct
from star2gps import DATA_FORMAT
from star2gps.storage import Storage, LOG_FOLDER, LOG_FILE_NAME

log = logging.getLogger(__name__)

def read_file() -> bytes:
    path = Storage.BASE_DIR / LOG_FOLDER / LOG_FILE_NAME
    if not path.exists():
        log.warning("Data file does not exist.")
        return b""

    record_struct = struct.Struct(DATA_FORMAT)
    with path.open("rb") as f:
        while True:
            chunk = f.read(record_struct.size)
            if not chunk:
                log.info("End of file reached.")
                break
        
            if len(chunk) < record_struct.size:
                log.warning("Partial record:", chunk)
                break

            lat, lon, alt = record_struct.unpack(chunk)
            print(f"Lat={lat}, Lon={lon}, Alt={alt}")

if __name__ == "__main__":
    read_file()