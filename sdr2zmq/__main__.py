#
# SDR2ZMQ
# Using RTL-SDR driver
# (2025) xaratustrah@github
#

import signal
import sys
import zmq
import toml
import numpy as np
from time import sleep
from loguru import logger
from rtlsdr import RtlSdr

# Function to validate the presence of required keys in the config
def validate_config(config):
    required_keys = {
        "sdr": ["sample_rate", "center_freq", "freq_correction", "gain"],
        "zmq": ["address"]
    }

    for section, keys in required_keys.items():
        if section not in config:
            raise KeyError(f"Missing section: {section}")
        for key in keys:
            if key not in config[section]:
                raise KeyError(f"Missing key: {key} in section: {section}")

def signal_handler(sig, frame):
    logger.info("Cancellation received, closing devices.")
    sdr.close()
    zmq_context.destroy()
    sys.exit(0)

def main():
    # Configure logging
    logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")

    # Load configuration from TOML file
    config = toml.load("config.toml")

    # Validate config
    try:
        validate_config(config)
    except KeyError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Initialize SDR
    sdr = RtlSdr()

    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Configure SDR using settings from TOML file
        sdr.sample_rate = config["sdr"]["sample_rate"]
        sdr.center_freq = config["sdr"]["center_freq"]
        sdr.freq_correction = config["sdr"]["freq_correction"]
        sdr.gain = config["sdr"]["gain"]
        sleep_time = config["sdr"]["sleep_time"]

        logger.info("SDR configured. Starting ZMQ publisher...")

        # Set up ZMQ context and PUB socket using settings from TOML file
        zmq_context = zmq.Context()
        publisher = zmq_context.socket(zmq.PUB)
        publisher.bind(config["zmq"]["address"])

        while True:
            samples = sdr.read_samples(2048)
            samples_float32 = np.vstack((samples.real, samples.imag)).reshape((-1,), order='F').astype(np.float32)
            #publisher.send(samples.tobytes())
            publisher.send(samples_float32.tobytes())
            logger.info("Published 2048 samples.")
            sleep(sleep_time)

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sdr.close()
        zmq_context.destroy()

#-------------------------
if __name__ == '__main__':
    main()
    