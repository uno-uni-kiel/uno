from flask import Request, render_template, session, redirect
from sqlite3 import Connection, Cursor
from refresh import get_refresh

def handle_lobby(con: Connection, cur: Cursor):
    if not "spieler_id" in session:
        return redirect("/")

    spieler_id = session["spieler_id"]

    spieler = cur.execute('''
        SELECT game_id FROM spieler WHERE id = ?
    ''', [ spieler_id ]).fetchone()
    game_id = spieler[0]

    if not game_id:
        return redirect("/dashboard")

    game = cur.execute('''
        SELECT name, refresh FROM game WHERE id = ?
    ''', [ game_id ]).fetchone()

    all_players = cur.execute('''
        SELECT position, name FROM spieler WHERE game_id = ?
    ''', [ game_id ]).fetchall()

    def sortByPosition(e):
        return e[0]

    all_players.sort(key = sortByPosition)

    return render_template("lobby.html", game = game, all_players = all_players, refresh = get_refresh(con, cur, game_id))