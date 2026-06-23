# SecondSight 
### Vision-Based Campus Navigation System

SecondSight is an intelligent, real-time navigation assistant designed to guide users along campus paths. By combining computer vision, obstacle avoidance, GPS routing, and intuitive audio/haptic feedback, it provides a comprehensive navigation system (particularly suited for visually impaired individuals).

> [!NOTE]
> * **Project Directory**: The root project folder is named `ss`.
> * **Prototype Scope**: This project is currently a prototype configured specifically for the **MNIT Jaipur** campus only.
> * **Adaptability & Future Scope**:
>   * The navigation checkpoints can be updated and modified for any other campus or location.
>   * Instead of hosting the backend on a local laptop server, the system can be scaled into a standalone mobile application (iOS/Android) connected to a centralized cloud server system.

---

##  Key Features

*   **Lane & Path Detection**: Uses OpenCV (HSV color thresholding and perspective warping) combined with **Artificial Potential Fields (APF)** to calculate path deviation and keep the user centered on the path.
*   **Intelligent Obstacle Avoidance**: Utilizes **YOLOv8** (Nano) to detect objects (people, vehicles, obstacles) and predicts potential collisions using a **Kalman Filter tracker**.
*   **Smart GPS Checkpoint Navigation**: Implements **Bi-directional BFS** to calculate the shortest path through a pre-mapped campus checkpoint graph.
*   **Multimodal Feedback**:
    *   **Text-to-Speech (TTS)**: Verbal navigation prompts and obstacle warnings.
    *   **Haptic Patterns**: Vibration intervals that change based on path deviation and blockage severity.
*   **Interactive Web Interface**: A responsive, web-based control panel for selecting destinations and viewing real-time camera overlays.
*   **Analytical Logging**: Automatically logs path deviation and obstacle blockages to local CSV files (`deviation_log.csv` and `blockage_log.csv`).

---

##  Repository Structure

*   `main.py`: The core FastAPI backend server serving detection, routing, location update, and log endpoints.
*   `index.html`: The HTML5/JavaScript frontend dashboard that handles camera access, GPS/compass polling, speech recognition, and haptic vibration.
*   `lane_detection.py`: Computer vision logic for path thresholding, warping, histogram analysis, and APF deviation calculations.
*   `object_detection.py`: YOLOv8 detection, Kalman Filter multi-object tracking, and intersection prediction.
*   `checkpoint_navigator.py`: Shortest-path routing (Bi-directional BFS), GPS coordinate distance calculation (Haversine), and checkpoint matching.
*   `logger.py`: CSV logging utilities for metrics collection.
*   `tts.py`: Python Text-to-Speech (`pyttsx3`) and speech-to-text recognition modules.
*   `extra_module.py`: Helper functions for image processing tasks.
*   `requirements.txt`: Python library dependencies.
*   `yolov8n.pt`: Pre-trained YOLOv8 weights.

---

##  Installation & Setup

### 1. Prerequisites
Ensure you have the following installed on your system:
*   Python 3.8 or higher
*   [Cloudflare Tunnel CLI (`cloudflared`)](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) (required for mobile deployment)

### 2. Install Dependencies
Navigate to the project folder and install the required packages:

```bash
# Navigate to the folder containing the project files
cd path/to/ss

# Create a virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate

# Install the Python packages
pip install -r requirements.txt
```

---

##  How to Run the Program

To run the program with full hardware integration (camera, GPS, and compass) on a mobile device, follow the steps below. This setup uses **Cloudflare Tunnels** to expose the local servers securely over HTTPS, which is required for mobile browsers to access camera and GPS APIs.

Open **4 separate terminal windows or tabs** and execute the commands:

### Tab 1: Start the FastAPI Backend
Start the backend server on `localhost:8000`:
```bash
cd path/to/ss
source venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8000
```

### Tab 2: Start the Frontend HTTP Server
Serve the frontend web app on `localhost:5500`:
```bash
cd path/to/ss
python3 -m http.server 5500
```

### Tab 3: Create Backend Tunnel
Expose the backend server to the internet via HTTPS:
```bash
cloudflared tunnel --url http://localhost:8000
```
*Take note of the generated HTTPS URL printed in the output (e.g., `https://xxxx.trycloudflare.com`).*

### Tab 4: Create Frontend Tunnel
Expose the frontend web app to the internet via HTTPS:
```bash
cloudflared tunnel --url http://localhost:5500
```
*Take note of the generated HTTPS URL.*

---

##  Using the Application

1. Open the **Frontend Tunnel HTTPS URL** (from Tab 4) on your mobile browser.
2. The page will search for the backend locally. When prompted, **paste the Backend Tunnel HTTPS URL** (from Tab 3) into the prompt dialog to connect the frontend to your tunnel-hosted backend.
3. Tap the microphone icon under **"Your Current Location"** and state where you are starting (e.g., "Hostel 4").
4. Tap the microphone icon under **"Where do you want to go"** and state your destination (e.g., "Library").
5. Review the route preview and tap **"Start Navigation"** to launch the camera feed, compass guidance, and real-time instructions.
