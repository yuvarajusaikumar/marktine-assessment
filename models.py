# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, time, date

db = SQLAlchemy()

class Doctor(db.Model):
    __tablename__ = "doctors"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    # working hours stored as simple strings "09:00", "17:00" for each day for simplicity
    work_start = db.Column(db.String, nullable=False, default="09:00")
    work_end = db.Column(db.String, nullable=False, default="17:00")

class Appointment(db.Model):
    __tablename__ = "appointments"
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    patient_name = db.Column(db.String, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    appt_type = db.Column(db.String, nullable=False)  # e.g., general, followup, physical, specialist
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    doctor = db.relationship("Doctor", backref="appointments")
