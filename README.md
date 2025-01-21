## HEALTH SIGNALS
## Team Members

| Name                  | Role                              |
|-----------------------|-----------------------------------|
| **George Mutale**     | Data Analysis, Database, AI      |
| **Rhyan Lubega**      | Backend                          |
| **Oscar Kyamuwendo**  | Data Collection and Hardware     |
| **Ebenezer Amakye**   | Frontend Development             |
| **Emmanuel Boaz**     | Security and Backend Development |

---

## Our project usecase

Our project, called **"PulseFlowBridge"**, is a web-based application designed to help monitor the heart rates of elderly people in real-time without requiring a nurse to constantly watch them. This system is aimed at making healthcare for the elderly more efficient and safer. The hospital doctors can create accounts on the platform and add patients as needed.

We use a **Bitalino sensor**, which can be placed either on a shirt near the chest or in a wristwatch, to measure heartbeats in real life. The sensor collects ECG signal data, and after cleaning and processing it, the system checks whether the heart rate is within the normal range. If the heart rate falls below **60 BPM** or exceeds **100 BPM**, the system automatically sends an alert to the hospital’s email. This alert includes the patient’s ID so that doctors can respond immediately and know who needs help.

This system reduces the need for constant manual monitoring by nurses, making it a **smart and efficient way to ensure the safety of elderly patients**.

---

## Evolution of our graph using images

## Challenges Faced

1. **Sensor Selection:**
   Initially, we planned to use the **Bitalino sensor** as the professors had planned, but due to Bluetooth connectivity failures of the sensor, we switched to an **AN ECG Arduino sensor**. However, this sensor came with limitations:
   - The electrode pads were one-time use, which reduced sensitivity over time.
   - Manual wire connections were prone to disconnection, leading to inaccurate results.

2. **Switching Back to Bitalino:**
   - The professor gave us a new the Bitalino sensor and downgraded Python to ensure compatibility.
   - We successfully connected the sensor directly to the frontend, enabling real-time visualization. However, this method produced inconsistent BPM values and incomplete peaks despite hardware buffering.

3. **Improving Data Accuracy:**
   - To address these issues, we collected data from the sensor and stored it in a **CSV file**. This file was then saved in a database.
   - By processing the stored data, we achieved accurate BPM readings and visualized graphs with well-defined peaks.
    
4. **Use of websocket:**
    - We are still debating whether the websocket is the perfect method to send real time data because we could get lags as we are visualising the graph

---

## Future Goals

- Acquire better sensors to improve real-time data acquisition and display.
- Enhance buffering and filtering techniques for more reliable data processing.
- Further refine our system for seamless real-time visualization.
- Making more research about how to send real time data without lags
- Creating an AI that defines scales for more visualisation and having a peak detection for different ecg signals
- Adding functionalities that can support to view live data of morethan 3 patients

---

