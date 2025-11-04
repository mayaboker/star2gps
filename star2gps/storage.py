

import pathlib
import logging
from star2gps import SingletonMeta
import struct
from  star2gps import DATA_FORMAT

log = logging.getLogger(__name__)

LOG_FOLDER = "log"
LOG_FILE_NAME = "gps_data.bin"

class Storage(metaclass=SingletonMeta):
    BASE_DIR = pathlib.Path(__file__).parent.parent

    def __init__(self):
        self.file = None
        self.__open_file()

    #region private
    def __get_data_path(self) -> pathlib.Path:
        full_path = Storage.BASE_DIR / LOG_FOLDER / LOG_FILE_NAME
        log.debug(f"Data path: {full_path}")
        return full_path
    
    def __open_file(self):
        try:
            data_path = self.__get_data_path()
            data_path.parent.mkdir(parents=True, exist_ok=True)
            self.file = data_path.open("wb")
        except Exception as e:
            log.exception("Failed to open storage file")
            raise e
    #endregion

    #region public
    def write(self, data) -> None:
        self.file.write(data)
    
    def close(self):
        if self.file:
            self.file.close()
            log.info("Storage file closed.")

    #endregion

    

    



if __name__ == "__main__":
    # storage = Storage()
    # storage.open_file()
    # storage.save_packed(b'\x01\x02\x03\x04')    
    Storage.read_file()