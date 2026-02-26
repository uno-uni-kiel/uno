from flask import Request, render_template, request, session
from sqlite3 import Connection, Cursor

import time
import random

def handle_game_simple(con: Connection, cur: Cursor):
    if not "spieler_id" in session:
        return redirect("/")

    spieler_id = session["spieler_id"]

    player_id, player_position, game_id = cur.execute('''
        SELECT id, position, game_id FROM spieler WHERE id = ?
    ''', [ spieler_id ]).fetchone()

    if not game_id:
        return redirect("/create_or_join")

    if request.method == "POST":
        if request.form["type"] == "draw":
            draw_card(con, cur, player_position, player_id, game_id)
        elif request.form["type"] == "place_card":
            place_card(con, cur, player_position, player_id, game_id, request.form["card_id"])

    game_name, game_deck_id, game_state, game_turn, game_current_card_id = cur.execute('''
        SELECT name, deck, state, turn, current_card_id FROM game WHERE id = ?
    ''', [ game_id ]).fetchone()

    if game_state == 0:
        return redirect("/lobby")

    all_players = cur.execute('''
        SELECT s.position, s.name, COUNT(z.simple_deck_id)
        FROM spieler s
        LEFT JOIN kartenzustand z ON s.id = z.ownership
        WHERE s.game_id = ?
        GROUP BY s.id
        ORDER BY s.position ASC
    ''', [ game_id ]).fetchall()

    player_cards = cur.execute('''
        SELECT d.id, t.farbe, t.wert 
        FROM kartenzustand z, simpledeck d, kartentyp t
        WHERE z.ownership = ? AND z.game_id = ? AND
            z.simple_deck_id = d.id AND d.kartentyp_id = t.id
    ''', [ player_id, game_id ]).fetchall()

    current_card_farbe, current_card_wert = cur.execute('''
        SELECT t.farbe, t.wert
        FROM simpledeck d, kartentyp t
        WHERE d.id = ? AND d.kartentyp_id = t.id
    ''', [ game_current_card_id ]).fetchone()

    return render_template(
        "game_simple.html", 
        all_players = all_players,
        player_id = player_id,
        player_position = player_position,
        player_cards = player_cards,
        game_turn = game_turn,
        game_current_card_id = game_current_card_id,
        current_card_farbe = current_card_farbe,
        current_card_wert = current_card_wert
    )

def start_game(con: Connection, cur: Cursor, game_id: int):
    # delete all players cards
    cur.execute('''
        DELETE FROM kartenzustand
        WHERE ownership IN (
            SELECT id FROM spieler WHERE game_id = ?
        )
    ''', [ game_id ])
    con.commit()

    all_player_ids = cur.execute('''
        SELECT id FROM spieler WHERE game_id = ?
    ''', [ game_id ]).fetchall()

    all_card_ids = cur.execute('''
        SELECT id FROM simpledeck
    ''').fetchall()

    # shuffle card stack
    random.shuffle(all_card_ids)

    for player_id in all_player_ids:
        # give player 7 cards
        for i in range(7):
            card_id = all_card_ids.pop()

            cur.execute('''
                INSERT INTO kartenzustand (simple_deck_id, ownership, game_id) VALUES (?, ?, ?)
            ''', [ card_id[0], player_id[0], game_id ])

    current_card_id = all_card_ids.pop()[0]

    cur.execute('''
        UPDATE game SET deck = ?, state = ?, current_card_id = ?, turn = ?, inverse_direction = ?, refresh = ? WHERE id = ?
    ''', [ 
        0, # deck (0 = simple)
        1, # state (1 = running)
        current_card_id,
        1, # turn
        0, # inverse direction
        round(time.time()), # refresh
        game_id
    ])
    con.commit()

def draw_card(con: Connection, cur: Cursor, player_position: int, player_id: int, game_id: int):
    print(player_id)

def place_card(con: Connection, cur: Cursor, player_position: int, player_id: int, game_id: int, card_id: int):
    game_name, game_deck_id, game_state, game_turn, game_current_card_id = cur.execute('''
        SELECT name, deck, state, turn, current_card_id FROM game WHERE id = ?
    ''', [ game_id ]).fetchone()

    # don't run if it isn't player's turn
    if game_turn != player_position:
        return

    # TODO: checks (game state, game turn, current_card_id matching etc)

    new_turn = game_turn + 1
    new_turn_player = cur.execute('''
        SELECT 1 FROM spieler WHERE game_id = ? AND position = ? LIMIT 1
    ''', [ game_id, new_turn ]).fetchone()

    # reset turn to 1 if no new player is found
    if new_turn_player is None:
        new_turn = 1

    # set current_card_id to card_id, set new turn value and update refresh value
    cur.execute('''
        UPDATE game SET current_card_id = ?, turn = ?, refresh = ? WHERE id = ?
    ''', [ card_id, new_turn, round(time.time()), game_id ])
    # delete kartenzustand
    cur.execute('''
        DELETE FROM kartenzustand WHERE simple_deck_id = ? AND ownership = ? AND game_id = ?
    ''', [ card_id, player_id, game_id ])
    con.commit()

    print(player_id)
