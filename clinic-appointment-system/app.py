
from flask import Flask, render_template, request, redirect
import sqlite3
import os

app = Flask(__name__)

DB = "clinic.db"

def get_db():
    return sqlite3.connect(DB)

def init_db():
    conn = get_db()
    conn.execute("CREATE TABLE IF NOT EXISTS patients (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, age INTEGER, phone TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS appointments (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER, date TEXT, time TEXT)")
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/add_patient", methods=["GET","POST"])
def add_patient():
    if request.method == "POST":
        name = request.form["name"]
        age = request.form["age"]
        phone = request.form["phone"]

        conn = get_db()
        conn.execute("INSERT INTO patients(name,age,phone) VALUES(?,?,?)",(name,age,phone))
        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("add_patient.html")

@app.route("/book", methods=["GET","POST"])
def book():
    conn = get_db()
    patients = conn.execute("SELECT * FROM patients").fetchall()

    if request.method == "POST":
        pid = request.form["patient"]
        date = request.form["date"]
        time = request.form["time"]

        conn.execute("INSERT INTO appointments(patient_id,date,time) VALUES(?,?,?)",(pid,date,time))
        conn.commit()
        conn.close()

        return redirect("/appointments")

    conn.close()
    return render_template("book_appointment.html", patients=patients)

@app.route("/appointments")
def appointments():
    conn = get_db()

    data = conn.execute("""
    SELECT appointments.id, patients.name, date, time
    FROM appointments
    JOIN patients
    ON patients.id = appointments.patient_id
    """).fetchall()

    conn.close()

    return render_template("appointments.html", data=data)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
