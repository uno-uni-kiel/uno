from flask import Flask, render_template, request, redirect
import sqlite3

from home import handle_home
from game import handle_game
from lobby import handle_lobby

app = Flask(__name__)

con = sqlite3.connect("uno.db", check_same_thread = False)
cur = con.cursor()

@app.route("/")
def home():
    return handle_home(request, con, cur)

@app.route("/game", methods = [ "GET", "POST" ])
def game():
    return handle_game(request, con, cur)

@app.route("/lobby", methods = [ "GET", "POST" ])
def lobby():
    return handle_lobby(request, con, cur)

@app.route("/refresh")
def refresh():
    return "hello"

if __name__ == "__main__":
    app.run(debug = True)