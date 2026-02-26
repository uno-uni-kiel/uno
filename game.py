from flask import Request, render_template, request, session, redirect
from sqlite3 import Connection, Cursor

def handle_game_end(con: Connection, cur: Cursor):
    if not "spieler_id" in session:
        return redirect("/")

    player_id = session["spieler_id"]
    game_id = cur.execute('''
        SELECT game_id FROM spieler WHERE id = ?
    ''', [ player_id ]).fetchone()[0]

    if not game_id:
        return redirect("/create_or_join")

    game_name, game_deck_id, game_state, game_winner_id = cur.execute('''
        SELECT name, deck, state, winner FROM game WHERE id = ?
    ''', [ game_id ]).fetchone()

    winner_name = cur.execute('''
        SELECT name FROM spieler WHERE id = ?
    ''', [ game_winner_id ]).fetchone()[0]

    if game_state == 0:
        return redirect("/lobby")

    if game_state == 1:
        if game_deck_id == 0:
            return redirect("/game/simple")
        elif game_deck_id == 1:
            return redirect("/game/complex")

    return render_template("game_end.html", winner_name = winner_name)

def handle_game_leave(con: Connection, cur: Cursor):
    if not "spieler_id" in session:
        return redirect("/")

    player_id = session["spieler_id"]
    game_id = cur.execute('''
        SELECT game_id FROM spieler WHERE id = ?
    ''', [ player_id ]).fetchone()[0]

    if not game_id:
        return redirect("/create_or_join")

    cur.execute('''
        UPDATE spieler SET game_id = NULL WHERE id = ?
    ''', [ player_id ]).fetchone()
    con.commit()

    return redirect("/")