# app.py
from flask import Flask, request, jsonify, render_template
from models import db, Doctor, Appointment
from datetime import datetime, timedelta, time
from dateutil import parser
import os

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "app.db")

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# Appointment type to duration (minutes)
APPT_DURATIONS = {
    "General Consultation": 30,
    "Follow-up": 15,
    "Physical Exam": 45,
    "Specialist Consultation": 60
}

def ensure_db():
    if not os.path.exists(DB_PATH):
        with app.app_context():
            db.create_all()
            # seed a doctor
            doc = Doctor(name="Dr. Mehta", work_start="09:00", work_end="17:00")
            db.session.add(doc)
            db.session.commit()

def parse_time_str(t_str):
    # "09:00" -> time(9,0)
    h,m = map(int, t_str.split(":"))
    return time(h,m)

def combine_date_time(d: datetime.date, t: time):
    return datetime.combine(d, t)

def overlaps(start1, end1, start2, end2):
    return start1 < end2 and start2 < end1

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/doctor/<int:doctor_id>/schedule", methods=["GET"])
def get_schedule(doctor_id):
    # Returns doctor's working hours and existing appointments for a date (optional)
    date_str = request.args.get("date")  # YYYY-MM-DD
    doc = Doctor.query.get_or_404(doctor_id)
    resp = {
        "doctor_id": doc.id,
        "name": doc.name,
        "work_start": doc.work_start,
        "work_end": doc.work_end,
    }
    if date_str:
        target = datetime.strptime(date_str, "%Y-%m-%d").date()
        appts = Appointment.query.filter(
            Appointment.doctor_id == doctor_id,
            Appointment.start_time >= datetime.combine(target, time(0,0)),
            Appointment.start_time < datetime.combine(target + timedelta(days=1), time(0,0))
        ).all()
        resp["appointments"] = [{
            "id": a.id,
            "patient_name": a.patient_name,
            "start_time": a.start_time.isoformat(),
            "end_time": a.end_time.isoformat(),
            "appt_type": a.appt_type
        } for a in appts]
    return jsonify(resp)

@app.route("/api/doctor/<int:doctor_id>/available", methods=["GET"])
def get_available_slots(doctor_id):
    """
    Query params:
     - date=YYYY-MM-DD (required)
     - appt_type (optional, default General Consultation)
     - step_minutes (optional, default 15) -> granularity with which we propose slots
    """
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error":"date param required YYYY-MM-DD"}), 400
    appt_type = request.args.get("appt_type", "General Consultation")
    step = int(request.args.get("step_minutes", 15))

    duration_min = APPT_DURATIONS.get(appt_type)
    if duration_min is None:
        return jsonify({"error":"unknown appt_type"}), 400

    doc = Doctor.query.get_or_404(doctor_id)
    target = datetime.strptime(date_str, "%Y-%m-%d").date()

    work_start = combine_date_time(target, parse_time_str(doc.work_start))
    work_end = combine_date_time(target, parse_time_str(doc.work_end))

    # fetch existing appointments for day
    appts = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.start_time >= datetime.combine(target, time(0,0)),
        Appointment.start_time < datetime.combine(target + timedelta(days=1), time(0,0))
    ).all()

    busy = [(a.start_time, a.end_time) for a in appts]

    slots = []
    current = work_start
    delta_step = timedelta(minutes=step)
    duration = timedelta(minutes=duration_min)

    while current + duration <= work_end:
        candidate_start = current
        candidate_end = current + duration

        conflict = False
        for bstart, bend in busy:
            if overlaps(candidate_start, candidate_end, bstart, bend):
                conflict = True
                break

        if not conflict:
            slots.append({
                "start": candidate_start.isoformat(),
                "end": candidate_end.isoformat()
            })
        current += delta_step

    return jsonify({
        "doctor_id": doctor_id,
        "date": date_str,
        "requested_appt_type": appt_type,
        "duration_minutes": duration_min,
        "slots": slots
    })

@app.route("/api/appointments", methods=["POST"])
def create_appointment():
    """
    payload:
    {
      "doctor_id": 1,
      "patient_name": "Charlie",
      "start": "2025-12-03T10:00:00",
      "appt_type": "General Consultation"
    }
    """
    data = request.get_json()
    required = ["doctor_id", "patient_name", "start", "appt_type"]
    if not all(k in data for k in required):
        return jsonify({"error":"missing fields"}), 400

    doctor_id = data["doctor_id"]
    patient_name = data["patient_name"]
    start = parser.isoparse(data["start"])
    appt_type = data["appt_type"]

    duration_min = APPT_DURATIONS.get(appt_type)
    if duration_min is None:
        return jsonify({"error":"unknown appt_type"}), 400

    end = start + timedelta(minutes=duration_min)

    # check working hours
    doc = Doctor.query.get_or_404(doctor_id)
    ddate = start.date()
    ws = combine_date_time(ddate, parse_time_str(doc.work_start))
    we = combine_date_time(ddate, parse_time_str(doc.work_end))
    if start < ws or end > we:
        return jsonify({"error":"appointment outside working hours"}), 400

    # check conflicts
    overlapping = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.start_time < end,
        Appointment.end_time > start
    ).first()
    if overlapping:
        return jsonify({"error":"time slot already taken", "overlap_with": overlapping.id}), 409

    appt = Appointment(
        doctor_id=doctor_id,
        patient_name=patient_name,
        start_time=start,
        end_time=end,
        appt_type=appt_type
    )
    db.session.add(appt)
    db.session.commit()

    return jsonify({
        "id": appt.id,
        "doctor_id": appt.doctor_id,
        "patient_name": appt.patient_name,
        "start_time": appt.start_time.isoformat(),
        "end_time": appt.end_time.isoformat(),
        "appt_type": appt.appt_type
    }), 201

if __name__ == "__main__":
    ensure_db()
    app.run(debug=True, port=5000)
