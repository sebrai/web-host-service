from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import os
import re
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
def check_acces(web_id,):
    if not session.get('user_id'):
      return (False,"not loged inn",("none",))
    if session['role'] == "admin":
        return (True,"admin user",("view", "edit", "remove"))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT u_id FROM websites where id = %s",(web_id,))
    creator_id = cursor.fetchone()
    if not creator_id:
        cursor.close()
        conn.close()
        abort(404)
    creator_id = creator_id['u_id']
    if creator_id == session['user_id']:
        cursor.close()
        conn.close()
        return (True,"accesed by creator",("view","edit","remove"))
    cursor.execute("SELECT EXISTS(SELECT 1 FROM private_acces WHERE web_id =%s AND u_id =%s ) AS 'acces'",(web_id,session['user_id']))
    has_acces = cursor.fetchone()["acces"]
    cursor.close()
    conn.close()
    # print(has_acces)
    return (bool(has_acces),"no exeptions hit",("view",))
    
 
#----------------------------------------------------- login
@app.route("/")
def blank():
    return redirect(url_for('login'))
@app.route("/login", methods=["GET", "POST"])
def login():
    if  session.get('user_id'):
      return redirect(url_for('home'))
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
            session['email'] = bruker['email']

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
    if not session.get('user_id'):
      return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, title, private FROM  websites WHERE u_id = %s",(session.get("user_id"),))
    websites = cursor.fetchall()
    # print(websites,session.get('user_id'))
    cursor.close()
    conn.close()
    return render_template("homepage.html",webpages = websites)

# -------------------------------------------------------------------- websites

@app.route("/visit/<web_id>")
def visit(web_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM web_user WHERE id = %s",(web_id,))
    result = cursor.fetchone()
    if not result: 
        cursor.close()
        conn.close()
        abort(404)
    cursor.close()
    conn.close()
    if result['private']:
        acces = check_acces(web_id=web_id)
        print(acces)
        if  not acces[0] or not "view" in acces[2]:
            abort(403)
    js = ("<script>"+result['js']+"</script>") if result.get("js") else ""
    css = ("<style>"+result['css']+"</style>") if result.get("css") else ""
    html_content,count = re.subn("(<title>)(.*?)(</title>)",rf"\1{result['title']}\3",result['html'], flags=re.IGNORECASE) 
    if count == 0:
        new_html = re.sub(r"(<head[^>]*>)", rf"\1\n<title>{result['title']}</title>", new_html, flags=re.IGNORECASE)
    html_content = re.sub(r'<script.*?>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    html_content = re.sub(r'<link[^>]*rel=["\']stylesheet["\'][^>]*>', '', html_content, flags=re.IGNORECASE)
    return css+ html_content + js

@app.route('/new_webpage', methods =['POST','GET'])
def newwebsite():
  if not session.get('user_id'):
      return redirect(url_for('login'))
  if request.method == 'POST':
    title = request.form['title']
    html = request.files['html']
    html_content = html.read().decode('utf-8')
    css = request.files.get('css')
    if css:
        css_content = css.read().decode('utf-8')
    js_file = request.files.get('js')
    if js_file:
        js_content = js_file.read().decode('utf-8')
    private = bool(request.form.get('private'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO websites(title,private, u_id,html,has_css,has_js) VALUES (%s,%s,%s,%s,%s,%s)",(title,private,session['user_id'],html_content,bool(css),bool(js_file)))
    conn.commit()
    cursor.execute("SELECT id FROM websites WHERE title = %s ORDER BY id DESC LIMIT 1",(title,))
    w_id = cursor.fetchone()[0]
    if css: 
        cursor.execute("INSERT INTO ext_files(type,w_id,content) VALUES (%s,%s,%s)", (1,w_id,css_content))
        conn.commit()
    if js_file: 
        cursor.execute("INSERT INTO ext_files(type,w_id,content) VALUES (%s,%s,%s)", (2,w_id,js_content))
        conn.commit()
    
    cursor.close()
    conn.close()
    return redirect(url_for('home'))
  return render_template("newweb.html")

@app.route("/change_status/<id>/<old>")
def changestatus(id,old):
    if not session.get('user_id'):
      return redirect(url_for('login'))
    new_status = 1 if int(old) == 0 else 0
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT u_id FROM websites WHERE id = %s",(id,))
    correct_id = cursor.fetchone()
    if correct_id and (correct_id['u_id'] == session['user_id'] or session['role'] == 'admin'):
        cursor.execute("UPDATE websites SET private = %s WHERE id = %s",(new_status,id))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('home'))
@app.route("/edit_website/<id>", methods =['POST','GET'])
def editweb(id):
    if not session.get('user_id'):
      return redirect(url_for('login'))
    acces = check_acces(id)
    if not acces[0] or not "edit" in acces[2]:
        abort(403)
    if request.method == 'POST':
        title = request.form['title']
        html = request.files['html']
        html_content = html.read().decode('utf-8')
        css = request.files.get('css')
        css_content = ""
        if css:
            css_content = css.read().decode('utf-8')
        js_file = request.files.get('js')
        js_content = ""
        if js_file:
            js_content = js_file.read().decode('utf-8')
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE websites SET title = %s, html = %s, has_css =%s, has_js = %s WHERE id =%s",(title,html_content,bool(css),bool(js_file),id))
        conn.commit()
        cursor.execute("SELECT 1 FROM ext_files WHERE w_id = %s AND type = 1", (id,))
        if cursor.fetchone(): # update row if it exists else instert new row
            cursor.execute("UPDATE ext_files SET content = %s WHERE w_id = %s AND type = 1", (css_content, id))
        else:
            cursor.execute("INSERT INTO ext_files (w_id, type, content) VALUES (%s, 1, %s)", (id, css_content))
       
       
        cursor.execute("SELECT 1 FROM ext_files WHERE w_id = %s AND type = 2", (id,))
        if cursor.fetchone():
            cursor.execute("UPDATE ext_files SET content = %s WHERE w_id = %s AND type = 2", (js_content, id))
        else:
            cursor.execute("INSERT INTO ext_files (w_id, type, content) VALUES (%s, 2, %s)", (id, js_content))
        conn.commit()
    
        cursor.close()
        conn.close()
        return redirect(url_for("home"))
    return render_template("editweb.html",id =id)  

@app.errorhandler(404)
def e404(e):
    path = request.path
    return render_template('404.html',path = path), 404

@app.errorhandler(403)
def e403(e):
    return redirect(url_for("home"))
if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0', port=5000)