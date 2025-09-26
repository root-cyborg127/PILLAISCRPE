from flask import Flask, render_template, jsonify, Response
import json
import os
import time
from datetime import datetime
import threading

app = Flask(__name__)

# --- Configuration ---
LOG_FILE = "automation_logs.txt"
DATA_FILE = "students_data.json"

class StudentDataManager:
    def __init__(self):
        self.data_file = DATA_FILE
        # Initial load and cache setup
        self.data_cache = self._load_data_from_file()

    def _load_data_from_file(self):
        """Loads data from the JSON file."""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"students": [], "last_updated": datetime.now().isoformat()}

    def refresh_cache(self):
        """Manually refresh the cache from the file."""
        new_data = self._load_data_from_file()
        if new_data:
            self.data_cache = new_data
            return True
        return False

    def get_student_by_id(self, student_id):
        """Retrieves single student detail from cache."""
        for student in self.data_cache.get("students", []):
            if student["student_id"] == student_id:
                return student
        return None

    def get_stats(self):
        """Calculates and returns dashboard statistics."""
        students = self.data_cache.get("students", [])
        total_students = len(students)
        last_updated = self.data_cache.get("last_updated", datetime.now().isoformat())
        
        # Stat: number of students with successful name extraction
        successful_students = sum(1 for s in students if s.get("student_name") not in [None, "Name Unknown", ""])
        
        return {
            "total_students": total_students,
            "successful_scrapes": successful_students,
            "last_updated": last_updated,
            "success_rate_percent": f"{successful_students / total_students * 100:.2f}%" if total_students > 0 else "0.00%"
        }

manager = StudentDataManager()

# --- Routes ---

@app.route("/")
def index():
    """Renders the main dashboard template."""
    return render_template("index.html")

@app.route("/api/students")
def get_students_summary():
    """Returns a summary of all student data for the grid view."""
    summary_data = {
        "last_updated": manager.data_cache.get("last_updated"),
        "students": [
            {
                "student_id": s.get("student_id"),
                "student_name": s.get("student_name"),
                "image_url": s.get("image_url"),
                "course_name": s.get("profile_data", {}).get("admission_details", {}).get("Course Name", "Unknown Course")
            }
            for s in manager.data_cache.get("students", [])
        ]
    }
    return jsonify(summary_data)

@app.route("/api/students/<student_id>")
def get_student_detail(student_id):
    """Returns all details for a single student ID."""
    student = manager.get_student_by_id(student_id)
    if student:
        return jsonify(student)
    return jsonify({"error": "Student not found"}), 404

@app.route("/api/stats")
def get_api_stats():
    """Returns computed statistics."""
    return jsonify(manager.get_stats())

@app.route("/api/data_refresh")
def data_refresh():
    """API endpoint to manually refresh the in-memory cache."""
    if manager.refresh_cache():
        return jsonify({"status": "success", "message": "Data cache refreshed."})
    else:
        return jsonify({"status": "warning", "message": "Cache refresh failed or file is empty."})

# --- Realtime logs (Server-Sent Events) ---
def generate_logs():
    """Reads logs from a file and streams them using Server-Sent Events (SSE)."""
    last_log_size = 0
    if not os.path.exists(LOG_FILE):
        yield f"data: [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Waiting for '{LOG_FILE}' to be created...\n\n"
    
    while True:
        try:
            if os.path.exists(LOG_FILE):
                current_size = os.path.getsize(LOG_FILE)
                if current_size < last_log_size:
                    # Log file was reset/truncated, start from beginning
                    last_log_size = 0
                
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    f.seek(last_log_size)
                    new_logs = f.read()
                    last_log_size = f.tell()
                    
                    if new_logs:
                        for line in new_logs.splitlines():
                            if line.strip():
                                yield f"data: {line.strip()}\n\n"
                                
        except Exception:
            # Silence file read/seek errors during stream
            pass
        
        time.sleep(1) # Check for new logs every second

@app.route("/api/logs")
def stream_logs():
    """Endpoint for streaming logs."""
    # Ensure cache is refreshed when accessing logs/dashboard
    manager.refresh_cache() 
    
    return Response(generate_logs(), mimetype="text/event-stream")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
