

import pathlib
import logging
from star2gps import SingletonMeta
import struct
from  star2gps import DATA_FORMAT

log = logging.getLogger(__name__)

class Storage(metaclass=SingletonMeta):
    BASE_DIR = pathlib.Path(__file__).parent.parent

    def __init__(self):
        self.file = self.open_file()

    def get_data_path(self) -> pathlib.Path:
        full_path = Storage.BASE_DIR / 'log' / "gps_data.bin" 
        log.debug(f"Data path: {full_path}")
        return full_path
    
    def open_file(self):
        data_path = self.get_data_path()
        data_path.parent.mkdir(parents=True, exist_ok=True)
        return data_path.open("wb")

    def write(self, data) -> None:
        self.file.write(data)
    
    def close(self):
        if self.file:
            self.file.close()
            log.info("Storage file closed.")

    @classmethod
    def read_file(cls) -> bytes:
        path = Storage.BASE_DIR / 'log' / "gps_data.bin" 
        if not path.exists():
            log.warning("Data file does not exist.")
            return b""
        
        record_struct = struct.Struct(DATA_FORMAT)
        with path.open("rb") as f:
            while True:
                chunk = f.read(record_struct.size)
                print("Read bytes:", len(chunk))
                if not chunk:
                    print("End of file reached.")
                    break
            
                if len(chunk) < record_struct.size:
                    print("Partial record:", chunk)
                    break

                lat, lon, alt = record_struct.unpack(chunk)
                print(f"Lat={lat}, Lon={lon}, Alt={alt}")

    



if __name__ == "__main__":
    # storage = Storage()
    # storage.open_file()
    # storage.save_packed(b'\x01\x02\x03\x04')    
    Storage.read_file()