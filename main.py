from flask import Flask, render_template, redirect, session
import sqlite3

from home import handle_home
from create_or_join import handle_create_or_join
from lobby import handle_lobby

from game import handle_game_end, handle_game_leave
from game_simple import handle_game_simple

from refresh import handle_refresh

app = Flask(__name__)
app.secret_key = '9^@w86n_@ws@m1jd_)7_&ayl@mm$9&pw9@noj*@)z)s9##dv$a'

con = sqlite3.connect("database.db", check_same_thread = False)
cur = con.cursor()

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

@app.route("/game/end", methods = [ "GET", "POST" ])
def game_end():
    return handle_game_end(con, cur)


@app.route("/game/leave", methods = [ "GET", "POST" ])
def game_leave():
    return handle_game_leave(con, cur)

@app.route("/debug/delete_games")
def debug_deleteGames():
    cur.execute("DELETE FROM Game")
    con.commit()
    return "DONE"

@app.route("/refresh")
def refresh():
    return handle_refresh(con, cur)

if __name__ == "__main__":
    app.run(debug = True, threaded = False)