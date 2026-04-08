from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import os
import climage
from dotenv import load_dotenv
# Bruker du Mariadb så bytter du ut mysql med mariadb. Mariadb må installeres med (pip install mariadb) Koden finner du på neste linje.
# import mariadb
load_dotenv()

user = os.getenv("user")
pword = os.getenv("p_word")
app = Flask(__name__)
app.secret_key = os.getenv("skey")

# Database-tilkobling
# bruker du Mariadb så bytter du ut mysql med mariadb. connect
# return mariadb.connect(
# Husk å endre host, user, password og database, slik at de er tilpasset dine instillinger 
def get_db_connection():
    return mysql.connector.connect(
        host="10.200.14.13",
        user=user,
        password=pword,
        database="web_hoster"
    )
#----------------------------------------------------- login
@app.route("/")
def blank():
    return redirect(url_for('login'))
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        brukernavn = request.form['brukernavn']
        passord = request.form['passord']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id,name,email,password,role FROM users WHERE name=%s", (brukernavn,))
        bruker = cursor.fetchone()
        cursor.close()
        conn.close()

        if bruker and check_password_hash(bruker['password'], passord):
            session['username'] = bruker['name']
            session['user_id'] = bruker['id']
            session['role'] = bruker['role']

            return redirect(url_for("home"))
        else:
            return render_template("login.html", feil_melding="Ugyldig brukernavn eller passord")

    return render_template("login.html")


@app.route("/new_user", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        brukernavn = request.form['brukernavn']
        epost = request.form['epost']
        passord = generate_password_hash(request.form['passord'])

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", 
                       (brukernavn, epost, passord))
        conn.commit()
        cursor.close()
        conn.close()
        flash("user registrert!", "success")
        return redirect(url_for("login"))

    return render_template("registrer.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("you have logged out", "info")
    return redirect(url_for("login"))

# ------------------------------------------------------------------ user info/ hamepage
@app.route("/user/<id>")
def user_page(id):
    return id+ " the user"

@app.route("/homepage")
def home():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.close()
    conn.close()
    return render_template("homepage.html")

# -------------------------------------------------------------------- websites

@app.route("/visit/<web_id>")
def visit(web_id):
    return web_id +" the site"

@app.errorhandler(404)
def e404(e):
    path = request.path
    return render_template('404.html',path = path)

if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0', port=5000)