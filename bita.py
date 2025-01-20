import os
import csv
import time

from bitalino import BITalino

# Configuration
MAC_ADDRESS = "98:D3:C1:FE:03:7F"  # Replace with your BITalino's MAC address
SAVE_FOLDER = "ecg_data"
FILENAME = "ecg_log.csv"
SAMPLING_RATE = 1000  # Changed to 1000 Hz to match sample data
CHANNELS = [1]  # Changed to channel 0 (A1 on BITalino)
DURATION = 10  # Duration to record in seconds

# Ensure the save folder exists
if not os.path.exists(SAVE_FOLDER):
    os.makedirs(SAVE_FOLDER)

# Full path for the output file
file_path = os.path.join(SAVE_FOLDER, FILENAME)

def save_data_to_csv(data):
    """Save the data to a CSV file."""
    mode = "w" if not os.path.exists(file_path) else "a"  # Append if file existsa
    with open(file_path, mode=mode, newline="") as file:
        writer = csv.writer(file)
        if mode == "w":  # Write header only when creating a new file
            writer.writerow(["timestamp", "ecg_value"])
        writer.writerows(data)

try:
    # Connect to BITalino
    print(f"Connecting to BITalino at {MAC_ADDRESS}...")
    device = BITalino(MAC_ADDRESS)

    # Start acquisition
    print("Starting data acquisition...")
    device.start(SAMPLING_RATE, CHANNELS)

    start_time = time.time()  # Capture the start time
    #start_time = int(time.time() * 1000)

    ecg_data = []

    while time.time() - start_time < DURATION:
        try:
            # Read samples (block size of 10)
            samples = device.read(10)
            
            for i, sample in enumerate(samples):
                timestamp = round((time.time() - start_time) + (i / SAMPLING_RATE), 3)
                ecg_value = sample[-1]  # ECG value is the last in the sample
                
                # Scale ECG value to match sample data range (approximately 470-540)
                scaled_ecg = int(ecg_value * (540 - 470) / 1023 + 470)
                
                ecg_data.append([timestamp, scaled_ecg])

        except Exception as read_error:
            print(f"Error reading data: {read_error}")
            break

    # Stop acquisition
    print("Stopping data acquisition...")
    device.stop()

    # Save data to CSV
    save_data_to_csv(ecg_data)
    print(f"Data saved to {file_path}")

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    # Ensure the device is released
    if 'device' in locals():
        device.close()
        print("Device disconnected.")
