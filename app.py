from flask import Flask, render_template, request, redirect, session, send_file, jsonify, send_from_directory
import sqlite3
import pandas as pd
import razorpay
import os

app = Flask(__name__)
app.secret_key = "admin_secret_key"

# ================= DATABASE =================

DB = "donations.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    db = get_db()

    # -------- ADMIN TABLE --------
    db.execute("""
    CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    # Default admin
    db.execute("INSERT OR IGNORE INTO admin (id, username, password) VALUES (1, 'admin', '1234')")

    # -------- DONATIONS TABLE --------
    db.execute("""
    CREATE TABLE IF NOT EXISTS donations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        amount INTEGER,
        payment_id TEXT
    )
    """)

    # -------- VOLUNTEERS TABLE --------
    db.execute("""
    CREATE TABLE IF NOT EXISTS volunteers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT NOT NULL,
        city TEXT NOT NULL,
        message TEXT
    )
    """)

    db.commit()
    db.close()

# ================= RAZORPAY =================

RAZORPAY_KEY_ID = "YOUR_KEY_ID"
RAZORPAY_KEY_SECRET = "YOUR_KEY_SECRET"

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# ================= PUBLIC ROUTES =================

@app.route("/")
def index():
    return render_template("index.html")
# ✅ ADD THIS PART HERE (robots route)
@app.route('/robots.txt')
def robots():
    return send_from_directory('static', 'robots.txt')

@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('static', 'sitemap.xml')
    
@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/mission")
def mission():
    return render_template("mission.html")

@app.route("/programs")
def programs():
    return render_template("programs.html")

@app.route("/team")
def team():
    return render_template("team.html")

# ================= DONATION =================

@app.route("/donation")
def donation():
    db = get_db()
    total = db.execute("SELECT SUM(amount) FROM donations").fetchone()[0]
    db.close()

    if total is None:
        total = 0

    return render_template("donation.html", total=total, key_id=RAZORPAY_KEY_ID)

@app.route("/create_order", methods=["POST"])
def create_order():
    amount = int(request.form["amount"]) * 100

    order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": "1"
    })

    return jsonify(order)

@app.route("/payment_success", methods=["POST"])
def payment_success():
    name = request.form["name"]
    email = request.form["email"]
    amount = request.form["amount"]
    payment_id = request.form["payment_id"]

    db = get_db()
    db.execute("INSERT INTO donations (name, email, amount, payment_id) VALUES (?, ?, ?, ?)",
               (name, email, amount, payment_id))
    db.commit()
    db.close()

    return "success"

# ================= VOLUNTEER =================

@app.route("/volunteer")
def volunteer():
    return render_template("volunteer.html")

@app.route("/register_volunteer", methods=["POST"])
def register_volunteer():
    name = request.form["name"]
    email = request.form["email"]
    phone = request.form["phone"]
    city = request.form["city"]
    message = request.form["message"]

    db = get_db()
    db.execute("""
        INSERT INTO volunteers (name, email, phone, city, message)
        VALUES (?, ?, ?, ?, ?)
    """, (name, email, phone, city, message))
    db.commit()
    db.close()

    return render_template("volunteer.html",
                           success="Thank you for joining as a Volunteer 🤝")

# ================= ADMIN LOGIN =================
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        admin = db.execute("SELECT * FROM admin WHERE username=? AND password=?",
                           (username, password)).fetchone()
        db.close()

        if admin:
            session["admin"] = username
            return redirect("/admin_dashboard")
        else:
            return render_template("admin_login.html", error="Invalid Credentials")

    return render_template("admin_login.html")
# ================= ADMIN DASHBOARD =================

@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect("/admin_login")

    db = get_db()

    total_donation = db.execute("SELECT SUM(amount) FROM donations").fetchone()[0]
    total_volunteers = db.execute("SELECT COUNT(*) FROM volunteers").fetchone()[0]
    total_donors = db.execute("SELECT COUNT(*) FROM donations").fetchone()[0]

    db.close()

    if total_donation is None:
        total_donation = 0

    return render_template("admin_dashboard.html",
                           total_donation=total_donation,
                           total_volunteers=total_volunteers,
                           total_donors=total_donors)

# ================= VIEW DONATIONS =================

@app.route("/admin_donations")
def admin_donations():
    if "admin" not in session:
        return redirect("/admin_login")

    db = get_db()
    donations = db.execute("SELECT * FROM donations").fetchall()
    db.close()

    return render_template("admin_donations.html", donations=donations)

@app.route("/delete_donation/<int:id>")
def delete_donation(id):
    db = get_db()
    db.execute("DELETE FROM donations WHERE id=?", (id,))
    db.commit()
    db.close()
    return redirect("/admin_donations")

# ================= VIEW VOLUNTEERS =================

@app.route("/admin_volunteers")
def admin_volunteers():
    if "admin" not in session:
        return redirect("/admin_login")

    db = get_db()
    volunteers = db.execute("SELECT * FROM volunteers").fetchall()
    db.close()

    return render_template("admin_volunteers.html", volunteers=volunteers)

@app.route("/delete_volunteer/<int:id>")
def delete_volunteer(id):
    db = get_db()
    db.execute("DELETE FROM volunteers WHERE id=?", (id,))
    db.commit()
    db.close()
    return redirect("/admin_volunteers")

# ================= EXPORT TO EXCEL =================

@app.route("/export_donations")
def export_donations():
    if "admin" not in session:
        return redirect("/admin_login")

    db = get_db()
    df = pd.read_sql_query("SELECT * FROM donations", db)
    db.close()

    file_path = "donations.xlsx"
    df.to_excel(file_path, index=False)

    return send_file(file_path, as_attachment=True)

# ================= RUN APP =================

if __name__ == "__main__":
    create_tables()
    app.run(debug=True)
