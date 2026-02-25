from flask import Request, render_template
from sqlite3 import Connection, Cursor

def handle_home(request: Request, con: Connection, cur: Cursor):
    return render_template("home.html")