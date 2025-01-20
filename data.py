import asyncio
import websockets
import pandas as pd
import json
import numpy as np
import scipy.signal as signal
import time

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
async def process_and_send_data_one_by_one(csv_file_path, uri):
    # Load ECG data from CSV
    ecg_data = pd.read_csv(csv_file_path)

    # Extract ECG values and timestamps
    timestamps = ecg_data['timestamp'].values
    ecg_values = ecg_data['ecg_value'].values

    # Convert ECG values to voltage
    voltages = convert_to_voltage(np.array(ecg_values))

    # Sampling frequency estimation
    fs = int(1 / (timestamps[1] - timestamps[0]))  # Assumes uniform sampling
    print(f"Sampling frequency (fs): {fs} Hz")

    # Filter and process ECG data
    filtered_ecg = low_pass_filter(ecg_values, fs)
    peaks = detect_r_peaks(filtered_ecg, fs)
    bpm = calculate_bpm(peaks, fs)

    print(f"Calculated BPM: {bpm}")

    # Use a fixed delay for testing (2 messages per second)
    fixed_delay = 0.01  # Adjust this value to control data rate (in seconds)

    last_sent_index = 0  # Track the last sent index

    # Loop to handle WebSocket reconnections
    while True:
        try:
            async with websockets.connect(uri, ping_interval=None, ping_timeout=4200) as websocket:
                print("Connected to WebSocket server.")
                last_sent_time = time.time()

                for index in range(last_sent_index, len(timestamps)):
                    timestamp = timestamps[index]
                    voltage = voltages[index]

                    current_time = time.time()
                    print(f"Time since last message: {current_time - last_sent_time:.3f} seconds")
                    last_sent_time = current_time

                    message = json.dumps({
                        "timestamp": timestamp,
                        "ecg": [voltage],  # Send as a list
                        "bpm": bpm
                    })

                    await websocket.send(message)
                    print(f"Sent: {message}")

                    last_sent_index = index + 1  # Update the last sent index

                    await asyncio.sleep(fixed_delay)

                break  # Exit loop after successfully sending all data

        except websockets.exceptions.ConnectionClosedOK:
            print("Connection closed by the server. Reconnecting...")
            await asyncio.sleep(2)  # Wait before reconnecting
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"Unexpected connection closure: {e}. Retrying...")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"Unexpected error: {e}. Retrying...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    csv_file_path = r"https://raw.githubusercontent.com/Health-signals/Sensor/refs/heads/main/ecg_log5.csv"
   
    websocket_uri = "ws://redesigned-tribble-q77q6pr9wq4jfx44w.github.dev/"  # Replace with your WebSocket server URI

    try:
        asyncio.run(process_and_send_data_one_by_one(csv_file_path, websocket_uri))
    except KeyboardInterrupt:
        print("Shutting down gracefully...")


