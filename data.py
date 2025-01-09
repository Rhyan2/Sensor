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
    return (ecg_signal / (adc_resolution )) * reference_voltage

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
    fixed_delay = 0.01# Adjust this value to control data rate (in seconds)

    # Loop to handle WebSocket reconnections
    while True:
        try:
            async with websockets.connect(uri, ping_interval=20, ping_timeout=10) as websocket:
                print("Connected to WebSocket server.")
                last_sent_time = time.time()

                for timestamp, voltage in zip(timestamps, voltages):
                    current_time = time.time()
                    print(f"Time since last message: {current_time - last_sent_time:.3f} seconds")
                    last_sent_time = current_time

                    # Prepare single data unit, ensure ecg is sent as a list
                    message = json.dumps({
                        "timestamp": timestamp,
                        "ecg": [voltage],  # Send as a list
                        "bpm": bpm
                    })

                    # Send the data
                    await websocket.send(message)
                    print(f"Sent: {message}")

                    # Apply fixed delay
                    await asyncio.sleep(fixed_delay)  # Use fixed delay to control sending rate

                # Exit loop after successfully sending all data
                break

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
    csv_file_path = r"C:\Users\Neu\Downloads\SampleECG.csv"  # Path to the uploaded CSV file
    websocket_uri = "ws://localhost:8000/ws/3"  # Replace with your WebSocket server URI

    try:
        asyncio.run(process_and_send_data_one_by_one(csv_file_path, websocket_uri))
    except KeyboardInterrupt:
        print("Shutting down gracefully...")










# import asyncio
# import websockets
# import serial
# import json
# import numpy as np
# import scipy.signal as signal

# # Low-pass filter function to remove high-frequency noise
# def low_pass_filter(ecg_signal, fs=100, cutoff=1.0):
#     nyquist = 0.5 * fs
#     normal_cutoff = cutoff / nyquist
#     b, a = signal.butter(1, normal_cutoff, btype='low', analog=False)
#     filtered_ecg = signal.filtfilt(b, a, ecg_signal)
#     return filtered_ecg

# # Bandpass filter and peak detection
# def detect_r_peaks(ecg_signal):
#     lowcut = 0.5  # Lower bound of heart rate (0.5 Hz = 30 BPM)
#     highcut = 5.0  # Upper bound of heart rate (5 Hz = 300 BPM)
#     fs = 100  # Sample rate (100 Hz)

#     nyquist = 0.5 * fs
#     low = lowcut / nyquist
#     high = highcut / nyquist
#     b, a = signal.butter(1, [low, high], btype='band')
#     filtered_ecg = signal.filtfilt(b, a, ecg_signal)

#     # Find R-peaks (local maxima) in the filtered ECG signal
#     peaks, _ = signal.find_peaks(filtered_ecg, distance=fs / 2)  # Adjust distance for heart rate
#     return peaks

# # Function to calculate BPM
# def calculate_bpm(peaks, sample_rate=100):
#     rr_intervals = np.diff(peaks) / sample_rate  # RR intervals in seconds
#     bpm = 60 / np.mean(rr_intervals) if len(rr_intervals) > 0 else 0
#     return bpm

# async def send_data_from_arduino():
#     # Connect to Arduino over serial
#     ser = serial.Serial('COM7', 9600)  # Adjust port to your system
#     uri = "ws://localhost:8000/ws/3"

#     ecg_signal = []  # Buffer for ECG data
#     noise_threshold = 100  # Initial noise threshold

#     while True:
#         try:
#             async with websockets.connect(uri, ping_interval=20, ping_timeout=10) as websocket:
#                 print("Connected to WebSocket server.")
#                 while True:
#                     if ser.in_waiting > 0:
#                         arduino_data = ser.readline().decode('utf-8').strip()
#                         try:
#                             data = json.loads(arduino_data)
#                             ecg_value = data['ecg']
#                             timestamp = data['timestamp']

#                             # Validate and filter ECG data
#                             if isinstance(ecg_value, (int, float)) and ecg_value > 0:
#                                 rolling_std = np.std(ecg_signal[-100:]) if len(ecg_signal) >= 100 else 0
#                                 if ecg_value > noise_threshold + rolling_std:
#                                     ecg_signal.append(ecg_value)
                                    
#                                     # Limit buffer size
#                                     if len(ecg_signal) > 1000:
#                                         ecg_signal = ecg_signal[-1000:]

#                                     if len(ecg_signal) > 100:  # Ensure enough data for processing
#                                         peaks = detect_r_peaks(np.array(ecg_signal))
#                                         bpm = calculate_bpm(peaks)
#                                         print(f"BPM: {bpm}")

#                                         message = json.dumps({
#                                             "ecg": ecg_signal[-50:],  # Send last 50 data points
#                                             "bpm": bpm,
#                                             "timestamp": timestamp
#                                         })
#                                         await websocket.send(message)
#                                         print(f"Sent: {message}")
#                                 else:
#                                     print("Filtered noise.")
#                             else:
#                                 print("Invalid data received.")
#                         except json.JSONDecodeError:
#                             print("JSON Decode Error")
                    
#                     await asyncio.sleep(0.1)
#         except websockets.exceptions.ConnectionClosed as e:
#             print(f"Connection closed: {e}. Reconnecting...")
#             await asyncio.sleep(2)
#         except asyncio.TimeoutError:
#             print("Connection timed out. Reconnecting...")
#             await asyncio.sleep(2)
#         except Exception as e:
#             print(f"Unexpected error: {e}. Retrying in 5 seconds...")
#             await asyncio.sleep(5)

# # Graceful shutdown handler
# if __name__ == "__main__":
#     try:
#         asyncio.run(send_data_from_arduino())
#     except KeyboardInterrupt:
#         print("Shutting down gracefully...")



# import asyncio
# import websockets
# #import bitalino
# import json
# import random
# import time
# import numpy as np
# from biosppy.signals import ecg
# import datetime



# async def send_random_data():
#     uri = "ws://localhost:8000/ws/3"
#     while True:
#         try:
#             async with websockets.connect(uri, ping_interval=20, ping_timeout=10) as websocket:
#                 print("Connected to the WebSocket server.")
#                 while True:
#                     ecg_value = random.uniform(-1, 1)
#                     bpm = random.uniform(60, 100)
#                     timestamp = datetime.datetime.now().isoformat() 
#                     message = json.dumps({
                        
#                         "ecg": [ecg_value],
#                         "timestamp": timestamp,
#                         "bpm": bpm
#                     })
#                     await websocket.send(message)
#                     print(f"Sent: {message}")
#                     await asyncio.sleep(1.5)
#         except websockets.exceptions.ConnectionClosed as e:
#             print(f"Connection closed: {e}. Reconnecting...")
#             await asyncio.sleep(2)
#         except asyncio.TimeoutError:
#             print("Connection timed out. Reconnecting...")
#             await asyncio.sleep(2)
#         except asyncio.CancelledError:
#             print("Task was cancelled. Exiting...")
#             break
        
#         except Exception as e:
#             print(f"Unexpected error: {e}. Retrying in 5 seconds...")
#             await asyncio.sleep(5)

# if __name__ == "__main__":
#     asyncio.run(send_random_data())
