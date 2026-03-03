from flask import Flask, render_template, redirect, session, make_response, send_from_directory
import sqlite3

from home import handle_home
from create_or_join import handle_create_or_join
from lobby import handle_lobby

from game import handle_game_end, handle_game_leave, handle_game_complex_wish
from game_simple import handle_game_simple
from game_complex import handle_game_complex

from refresh import handle_refresh

app = Flask(__name__, static_folder = None)
# secret key for session
app.secret_key = '9^@w86n_@ws@m1jd_)7_&ayl@mm$9&pw9@noj*@)z)s9##dv$a'

con = sqlite3.connect("database.db", check_same_thread = False)
cur = con.cursor()

# register routes

@app.route("/", methods = [ "GET", "POST" ])
def home():
    return handle_home(con, cur)

@app.route("/create_or_join", methods = [ "GET", "POST" ])
def create_or_join():
    return handle_create_or_join(con, cur)

@app.route("/lobby", methods = [ "GET", "POST" ])
def lobby():
    return handle_lobby(con, cur)

@app.route("/game/simple", methods = [ "GET", "POST" ])
def game_simple():
    return handle_game_simple(con, cur)

@app.route("/game/complex", methods = [ "GET", "POST" ])
def game_complex():
    return handle_game_complex(con, cur)

@app.route("/game/complex/wish", methods = [ "POST" ])
def game_complex_wish():
    return handle_game_complex_wish(con, cur)

@app.route("/game/end", methods = [ "GET", "POST" ])
def game_end():
    return handle_game_end(con, cur)

@app.route("/game/leave", methods = [ "GET", "POST" ])
def game_leave():
    return handle_game_leave(con, cur)

@app.route("/debug/clean")
def debug_clean():
    cur.execute("DELETE FROM game")
    cur.execute("DELETE FROM spieler")
    cur.execute("DELETE FROM kartenzustand")
    con.commit()
    return redirect("/")

@app.route("/refresh")
def refresh():
    return handle_refresh(con, cur)

# override static folder to enable caching
@app.route('/static/<path:filename>')
def static(filename):
    res = make_response(send_from_directory('static/', filename))
    res.headers['Cache-Control'] = 'max-age'
    return res

if __name__ == "__main__":
    app.run(debug = True, threaded = False)