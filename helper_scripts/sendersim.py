import zmq
import numpy as np
import time
import sys
import select
from loguru import logger

lframe = 2048

def generate_noisy_sine_wave(freq=100, amplitude=1):
    t = np.linspace(0, 1, lframe)
    sine_wave = amplitude * np.sin(2 * np.pi * freq * t)
    noise = np.random.normal(0, 0.1, sine_wave.shape)
    return (sine_wave + noise).astype(np.float32)

context = zmq.Context()
socket = zmq.Socket(context, zmq.PUB)
socket.bind("tcp://*:5555")

logger.add("sender_log.log", rotation="1 MB")  # Log file with rotation

logger.info("Now sending, press enter to send signal, or press Ctrl-C to abort...")

while True:
    try:
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            _ = sys.stdin.read(1)
            send_sine_wave = True
            logger.info("Sending signal...")
        else:
            send_sine_wave = False

        if send_sine_wave:
            data = generate_noisy_sine_wave(200, 1) + generate_noisy_sine_wave(160, 0.4)
        else:
            data = generate_noisy_sine_wave(200, 1)
            #data = np.random.normal(0, 0.1, lframe).astype(np.float32)

        data *= 1e-6  # Multiply everything by 1e-6
        socket.send(data.tobytes())
        time.sleep(0.1)
        
    except KeyboardInterrupt:
        logger.success("\nAborted by user.")
        break
