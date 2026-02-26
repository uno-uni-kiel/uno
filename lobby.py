from flask import Request, render_template, request, session, redirect
from sqlite3 import Connection, Cursor
from refresh import get_refresh
import time

import game_simple

def handle_lobby(con: Connection, cur: Cursor):
    if not "spieler_id" in session:
        return redirect("/")

    spieler_id = session["spieler_id"]

    spieler = cur.execute('''
        SELECT game_id FROM spieler WHERE id = ?
    ''', [ spieler_id ]).fetchone()
    game_id = spieler[0]

    if not game_id:
        return redirect("/create_or_join")

    game = cur.execute('''
        SELECT name, deck, state FROM game WHERE id = ?
    ''', [ game_id ]).fetchone()

    game_name = game[0]
    game_deck_id = game[1]
    game_state = game[2]

    all_players = cur.execute('''
        SELECT position, name FROM spieler WHERE game_id = ?
    ''', [ game_id ]).fetchall()

    def sortByPosition(e):
        return e[0]

    all_players.sort(key = sortByPosition)

    if request.method == "POST":
        if request.form["type"] == "select_deck":
            deck = request.form["deck"]

            if deck == "simple":
                game_deck_id = 0
            elif deck == "complex":
                game_deck_id = 1

            cur.execute('''
                UPDATE game SET deck = ?, refresh = ? WHERE id = ?
            ''', [ game_deck_id, round(time.time()), game_id ])
            con.commit()
        if request.form["type"] == "start":
            if game_deck_id == 0:
                game_simple.start_game(con, cur, game_id)
                game_state = 1
            elif game_deck_id == 1:
                # todo
                print("not implemented yet")
    
    # game is running, redirect to game route
    if game_state == 1:
        if game_deck_id == 0:
            return redirect("/game-simple")
        elif game_deck_id == 1:
            return redirect("/game-complex")

    return render_template(
        "lobby.html", 
        game_name = game_name, 
        game_deck_id = game_deck_id, 
        all_players = all_players, 
        refresh = get_refresh(con, cur, game_id)
    )