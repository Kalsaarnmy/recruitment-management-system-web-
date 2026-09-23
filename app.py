from flask import Flask, render_template, request, redirect, session, send_from_directory, Response
import sqlite3
import os
import csv
import io

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key") # Secret key untuk session

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def init_db():
    conn = sqlite3.connect("labamen.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pendaftar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT NOT NULL,
            nim TEXT NOT NULL,
            prodi TEXT NOT NULL,
            email TEXT NOT NULL,
            whatsapp TEXT NOT NULL,
            divisi TEXT NOT NULL,
            alasan TEXT NOT NULL,
            berkas TEXT,
            status TEXT DEFAULT 'Diproses'
        )
    """)

    conn.commit()
    conn.close()


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/daftar", methods=["GET", "POST"])
def daftar():
    if request.method == "POST":
        nama = request.form["nama"]
        nim = request.form["nim"]
        prodi = request.form["prodi"]
        email = request.form["email"]
        whatsapp = request.form["whatsapp"]
        divisi = request.form["divisi"]
        alasan = request.form["alasan"]

        file = request.files["berkas"]
        nama_file = ""

        if file and file.filename != "":
            nama_file = file.filename
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], nama_file))

        conn = sqlite3.connect("labamen.db")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO pendaftar 
            (nama, nim, prodi, email, whatsapp, divisi, alasan, berkas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (nama, nim, prodi, email, whatsapp, divisi, alasan, nama_file))

        conn.commit()
        conn.close()

        return redirect("/sukses")

    return render_template("daftar.html")

@app.route("/sukses")
def sukses():
    return render_template("sukses.html")


@app.route("/dashboard")
def dashboard():
    if "admin" not in session:
        return redirect("/login")

    keyword = request.args.get("keyword", "")
    divisi_filter = request.args.get("divisi", "")
    status_filter = request.args.get("status", "")

    conn = sqlite3.connect("labamen.db")
    cursor = conn.cursor()

    query = "SELECT * FROM pendaftar WHERE 1=1"
    params = []

    if keyword:
        query += " AND (nama LIKE ? OR nim LIKE ? OR email LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])

    if divisi_filter:
        query += " AND divisi = ?"
        params.append(divisi_filter)

    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)

    cursor.execute(query, params)
    data = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM pendaftar")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM pendaftar WHERE status = 'Diproses'")
    diproses = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM pendaftar WHERE status = 'Lolos'")
    lolos = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM pendaftar WHERE status = 'Tidak Lolos'")
    tidak_lolos = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "dashboard.html",
        data=data,
        total=total,
        diproses=diproses,
        lolos=lolos,
        tidak_lolos=tidak_lolos,
        keyword=keyword,
        divisi_filter=divisi_filter,
        status_filter=status_filter
    )

@app.route("/hapus/<int:id>")
def hapus(id):
    conn = sqlite3.connect("labamen.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM pendaftar WHERE id = ?", (id,))

    conn.commit()
    conn.close()

    return redirect("/dashboard")


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    conn = sqlite3.connect("labamen.db")
    cursor = conn.cursor()

    if request.method == "POST":
        nama = request.form["nama"]
        nim = request.form["nim"]
        prodi = request.form["prodi"]
        email = request.form["email"]
        whatsapp = request.form["whatsapp"]
        divisi = request.form["divisi"]
        alasan = request.form["alasan"]
        status = request.form["status"]

        cursor.execute("""
            UPDATE pendaftar
            SET nama = ?, nim = ?, prodi = ?, email = ?, whatsapp = ?, divisi = ?, alasan = ?, status = ?
            WHERE id = ?
        """, (nama, nim, prodi, email, whatsapp, divisi, alasan, status, id))

        conn.commit()
        conn.close()

        return redirect("/dashboard")

    cursor.execute("SELECT * FROM pendaftar WHERE id = ?", (id,))
    peserta = cursor.fetchone()

    conn.close()

    return render_template("edit.html", peserta=peserta)

@app.route("/login", methods=["GET", "POST"]) # login admin sederhana, username: admin, password: admin123
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":
            session["admin"] = True
            return redirect("/dashboard")
        else:
            return render_template("login.html", error="Username atau password salah!")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/")


@app.route("/uploads/<filename>")
def lihat_berkas(filename):
    if "admin" not in session:
        return redirect("/login")

    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/export")
def export_data():
    if "admin" not in session:
        return redirect("/login")

    conn = sqlite3.connect("labamen.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM pendaftar")
    data = cursor.fetchall()

    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "ID", "Nama", "NIM", "Prodi", "Email",
        "WhatsApp", "Divisi", "Alasan", "Berkas", "Status"
    ])

    writer.writerows(data)

    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=data_pendaftar_labamen.csv"

    return response


if __name__ == "__main__":
    init_db()
    app.run(debug=True)