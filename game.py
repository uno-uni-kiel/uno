from flask import Request, render_template, request
from sqlite3 import Connection, Cursor

def handle_game(con: Connection, cur: Cursor):
    return render_template("game.html")