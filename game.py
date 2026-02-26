from flask import Request, render_template, request, session, redirect
from sqlite3 import Connection, Cursor

def handle_game_end(con: Connection, cur: Cursor):
    if not "spieler_id" in session:
        return redirect("/")

    player_id = session["spieler_id"]
    game_id = cur.execute('''
        SELECT game_id FROM spieler WHERE id = ?
    ''', [ player_id ]).fetchone()[0]

    # redirect if player hasn't joined a game
    if not game_id:
        return redirect("/create_or_join")

    # retrieve game info
    game_deck_id, game_state, game_winner_id = cur.execute('''
        SELECT deck, state, winner FROM game WHERE id = ?
    ''', [ game_id ]).fetchone()

    # redirect to lobby if game hasn't started yet
    if game_state == 0:
        return redirect("/lobby")

    # redirect to game page if game is still running
    if game_state == 1:
        if game_deck_id == 0:
            return redirect("/game/simple")
        elif game_deck_id == 1:
            return redirect("/game/complex")

    # retrieve winnner name
    winner_name = cur.execute('''
        SELECT name FROM spieler WHERE id = ?
    ''', [ game_winner_id ]).fetchone()[0]

    return render_template("game_end.html", winner_name = winner_name)

def handle_game_leave(con: Connection, cur: Cursor):
    if not "spieler_id" in session:
        return redirect("/")

    player_id = session["spieler_id"]
    game_id = cur.execute('''
        SELECT game_id FROM spieler WHERE id = ?
    ''', [ player_id ]).fetchone()[0]

    # redirect if player hasn't joined a game
    if not game_id:
        return redirect("/create_or_join")

    # set game_id of player to NULL
    cur.execute('''
        UPDATE spieler SET game_id = NULL WHERE id = ?
    ''', [ player_id ]).fetchone()
    con.commit()

    # redirect to main page
    return redirect("/")