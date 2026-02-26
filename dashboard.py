from flask import Request, render_template, request, session, redirect
from sqlite3 import Connection, Cursor
from refresh import refresh

def handle_dashboard(con: Connection, cur: Cursor):
    if not "spieler_id" in session:
        return redirect("/")

    spieler_id = session["spieler_id"]

    if request.method == "POST":
        if request.form["type"] == "create":
            name = request.form["name"]

            cur.execute('''
                INSERT INTO game (name, state)
                VALUES (?, 0)
                RETURNING id
            ''', [name])

            game_id = cur.fetchone()[0]
            con.commit()
        if request.form["type"] == "join":
            game_id = request.form["game_id"]   

        next_position = cur.execute('''
            SELECT COUNT(name) FROM spieler WHERE game_id = ?
        ''', [ game_id ]).fetchone()[0] + 1

        cur.execute('''
             UPDATE spieler SET game_id = ?, position = ? WHERE id = ?
        ''', [game_id, next_position, spieler_id])

        session["game_id"] = game_id
        refresh(con, cur, game_id)
        
        return redirect("/lobby")

    def only_lobby(g):
        return g[2] == 0

    res = cur.execute('''
        SELECT id, name, state FROM Game
    ''').fetchall()
    return render_template("dashboard.html", games = filter(only_lobby, res))