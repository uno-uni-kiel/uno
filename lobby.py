from flask import Request, render_template, request, session, redirect
from sqlite3 import Connection, Cursor
import time

import game_simple
import game_complex

def handle_lobby(con: Connection, cur: Cursor):
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
    game_name, game_deck_id, game_state = cur.execute('''
        SELECT name, deck, state FROM game WHERE id = ?
    ''', [ game_id ]).fetchone()

    # actions
    if request.method == "POST":
        # select the deck to play with
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
        # start the game
        if request.form["type"] == "start":
            # address player positions
            # retrieve all joined player ids randomly
            all_player_ids = cur.execute('''
                SELECT id FROM spieler WHERE game_id = ? ORDER BY random()
            ''', [ game_id ]).fetchall()

            next_position = 0
            for player_id in all_player_ids:
                next_position += 1

                all_players = cur.execute('''
                    UPDATE spieler SET position = ? WHERE id = ?
                ''', [ next_position, player_id[0] ]).fetchall()

            if game_deck_id == 0:
                game_simple.start_game(con, cur, game_id)
                game_state = 1
            elif game_deck_id == 1:
                game_complex.start_game(con, cur, game_id)
                game_state = 1

    # redirect to game page if game is running
    if game_state == 1:
        if game_deck_id == 0:
            return redirect("/game/simple")
        elif game_deck_id == 1:
            return redirect("/game/complex")
    # redirect to game end page if game has ended
    elif game_state == 2:
        return redirect("/game/end")

    # retrieve all players that joined the game
    all_players = cur.execute('''
        SELECT name FROM spieler WHERE game_id = ?
    ''', [ game_id ]).fetchall()

    return render_template(
        "lobby.html", 
        game_name = game_name, 
        game_deck_id = game_deck_id, 
        all_players = all_players
    )