import time
import random

def generate_values(initial_temp: int = 25, initial_humidity: int = 40):
    temperature = initial_temp
    humidity = initial_humidity
    while True:
        temperature += random.randint(-1, 1)
        humidity += random.randint(-2, 2)
        humidity = max(0, min(100, humidity))
        yield humidity, temperature

def run_dht_simulator(delay, callback, stop_event, code: str = "DHT1"):
    for h, t in generate_values():
        time.sleep(delay)
        callback(h, t, code)
        if stop_event.is_set():
            break
