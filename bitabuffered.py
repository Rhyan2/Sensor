import os
import asyncio
import websockets
import csv
import json
import numpy as np
from bitalino import BITalino
import scipy.signal as signal
import time

# Configuration
MAC_ADDRESS = "98:D3:C1:FE:03:7F"  # Replace with your BITalino's MAC address
WEBSOCKET_URI = "ws://localhost:8000/ws/3"  # Replace with your WebSocket server URI
SAMPLING_RATE = 1000  # Adjust sampling rate
CHANNELS = [1]  # ECG channel on BITalino
DURATION = 1000  # Duration to record in seconds

# Low-pass filter function to remove high-frequency noise
def low_pass_filter(ecg_signal, fs=100, cutoff=1.0):
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    b, a = signal.butter(1, normal_cutoff, btype='low', analog=False)
    filtered_ecg = signal.filtfilt(b, a, ecg_signal)
    return filtered_ecg

# Bandpass filter and peak detection
def detect_r_peaks(ecg_signal, fs=100):
    lowcut = 0.5  # Lower bound of heart rate (0.5 Hz = 30 BPM)
    highcut = 5.0  # Upper bound of heart rate (5 Hz = 300 BPM)

    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = signal.butter(1, [low, high], btype='band')
    filtered_ecg = signal.filtfilt(b, a, ecg_signal)

    # Find R-peaks (local maxima) in the filtered ECG signal
    peaks, _ = signal.find_peaks(filtered_ecg, distance=fs / 2)  # Adjust distance for heart rate
    return peaks

# Function to calculate BPM
def calculate_bpm(peaks, sample_rate=100):
    rr_intervals = np.diff(peaks) / sample_rate  # RR intervals in seconds
    bpm = 60 / np.mean(rr_intervals) if len(rr_intervals) > 0 else 0
    return bpm

# Convert raw ADC values to voltage
def convert_to_voltage(ecg_signal, adc_resolution=1024, reference_voltage=3.3):
    return (ecg_signal / adc_resolution) * reference_voltage

# Process and send data over WebSocket
async def acquire_and_send_data():
    try:
        print(f"Connecting to BITalino at {MAC_ADDRESS}...")
        device = BITalino(MAC_ADDRESS)

        # Start acquisition
        print("Starting data acquisition...")
        device.start(SAMPLING_RATE, CHANNELS)

        ecg_data = []
        #start_time = int(time.time() * 1000)

        start_time = time.time()  # Capture the start time

        async with websockets.connect(WEBSOCKET_URI, ping_interval=20, ping_timeout=10) as websocket:
            print("Connected to WebSocket server.")
            while time.time() - start_time < DURATION:
                try:
                    # Read samples (block size of 10)
                    samples = device.read(10)

                    for i, sample in enumerate(samples):
                        timestamp = round((time.time() - start_time) + (i / SAMPLING_RATE), 3)
                        ecg_value = sample[-1]  # ECG value is the last in the sample

                        # Scale ECG value
                        scaled_ecg = int(ecg_value * (540 - 470) / 1023 + 470)
                        ecg_data.append(scaled_ecg)

                        # Filter and process ECG data in real-time
                        if len(ecg_data) > SAMPLING_RATE:  # Only process if we have 1 second of data
                            windowed_data = ecg_data[-SAMPLING_RATE:]  # Last second of data
                            filtered_ecg = low_pass_filter(windowed_data, SAMPLING_RATE)
                            peaks = detect_r_peaks(filtered_ecg, SAMPLING_RATE)
                            bpm = calculate_bpm(peaks, SAMPLING_RATE)

                            # Convert to voltage
                            voltage = convert_to_voltage(scaled_ecg)

                            # Prepare and send the message
                            message = json.dumps({
                                "timestamp": timestamp,
                                "ecg": [voltage],
                                "bpm": bpm
                            })
                            await websocket.send(message)
                            print(f"Sent: {message}")

                        await asyncio.sleep(0.01)  # Control data rate

                except Exception as read_error:
                    print(f"Error reading data: {read_error}")
                    break

        print("Stopping data acquisition...")
        device.stop()

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # Ensure the device is released
        if 'device' in locals():
            device.close()
            print("Device disconnected.")

if __name__ == "__main__":
    try:
        asyncio.run(acquire_and_send_data())
    except KeyboardInterrupt:
        print("Shutting down gracefully...")
