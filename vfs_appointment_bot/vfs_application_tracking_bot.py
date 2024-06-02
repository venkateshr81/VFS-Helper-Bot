import sys
import logging

from logging.config import fileConfig
from _Timer import countdown
from _ConfigReader import _ConfigReader
from _VfsClient import _VfsClient

def _input():
    print("Enter the reference number: ")
    reference_number = input()

    print("Enter the last name: ")
    last_name = input()

    logging.debug("Reference number: {}, Last name: {}".format(reference_number, last_name))

    return reference_number, last_name

def _read_command_line_args():
    if len(sys.argv) != 3:
        return _input()
    return sys.argv[1], sys.argv[2]


if __name__ == "__main__":
    count = 1
    fileConfig('config/logging.ini')
    logging = logging.getLogger(__name__);

    _vfs_client = _VfsClient()
    _config_reader = _ConfigReader()
    _interval = _config_reader.read_prop("DEFAULT", "interval")
    logging.debug("Interval: {}".format(_interval))

    reference_number, last_name = _read_command_line_args()

    logging.info("Starting VFS Application Tracking Bot")
    while True:
        try:
            logging.info("Running VFS Application Tracking Bot: Attempt#{}".format(count))
            _vfs_client.track_application(reference_number=reference_number, last_name=last_name)
            logging.debug("Sleeping for {} seconds".format(_interval))
            countdown(int(_interval))
        except Exception as e:
            logging.info(e.args[0] + ". Please check the logs for more details")
            logging.debug(e, exc_info=True, stack_info=True)
            countdown(int(60))
            pass
        print("\n")
        count += 1