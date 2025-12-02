-- schema.sql
DROP TABLE IF EXISTS appointments;
DROP TABLE IF EXISTS doctors;

CREATE TABLE doctors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    work_start TEXT NOT NULL,
    work_end TEXT NOT NULL
);

CREATE TABLE appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id INTEGER NOT NULL,
    patient_name TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    appt_type TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(doctor_id) REFERENCES doctors(id)
);

-- seed
INSERT INTO doctors (name, work_start, work_end) VALUES ('Dr. Mehta', '09:00', '17:00');

-- sample existing appointment
INSERT INTO appointments (doctor_id, patient_name, start_time, end_time, appt_type) VALUES
(1, 'Alice', '2025-12-03 09:30:00', '2025-12-03 10:00:00', 'General Consultation'),
(1, 'Bob', '2025-12-03 11:00:00', '2025-12-03 11:15:00', 'Follow-up');
