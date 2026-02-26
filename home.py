from flask import Request, render_template, request, session, redirect
from sqlite3 import Connection, Cursor

def handle_home(con: Connection, cur: Cursor):
    # redirect if user already created a player
    if "spieler_id" in session:
        return redirect("create_or_join")

    # actions
    if request.method == "POST":
        # create new player
        name = request.form["name"]
        cur.execute('''
            INSERT INTO spieler (name)
            VALUES (?)
            RETURNING id
        ''', [name])

        new_id = cur.fetchone()[0]
        con.commit()

        session["spieler_id"] = new_id
        return redirect("create_or_join")

    return render_template("home.html")