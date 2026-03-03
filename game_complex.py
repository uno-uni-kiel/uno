from flask import Request, render_template, request, session, redirect
from sqlite3 import Connection, Cursor

import time
import random

def handle_game_complex(con: Connection, cur: Cursor):
    if not "spieler_id" in session:
        return redirect("/")

    player_id = session["spieler_id"]
    player_position, game_id, player_uno = cur.execute('''
        SELECT position, game_id, uno FROM spieler WHERE id = ?
    ''', [ player_id ]).fetchone()

    # redirect if player isn't in any game
    if not game_id:
        return redirect("/create_or_join")

    # actions
    if request.method == "POST":
        if request.form["type"] == "draw":
            # draw a card
            draw_card(
                con = con, 
                cur = cur, 
                player_position = player_position, 
                player_id = player_id, 
                player_uno = player_uno, 
                game_id = game_id
            )
        elif request.form["type"] == "place_card":
            # place a card
            place_card(
                con = con, 
                cur = cur, 
                player_position = player_position, 
                player_id = player_id, 
                player_uno = player_uno, 
                game_id = game_id, 
                card_id = request.form["card_id"], 
                new_wish_farbe = int(request.form["wish_farbe"]) if "wish_farbe" in request.form 
                    else None
            )
        elif request.form["type"] == "uno":
            # press 'uno' button
            uno(
                con = con, 
                cur = cur, 
                player_id = player_id, 
                player_uno = player_uno, 
                game_id = game_id
            )

    # retrieve game info
    game_name, game_deck_id, game_state, game_turn, game_draw_stack, game_wish_farbe, game_current_card_id = cur.execute('''
        SELECT name, deck, state, turn, draw_stack, wish_farbe, current_card_id FROM game WHERE id = ?
    ''', [ game_id ]).fetchone()

    # redirect to lobby if game hasn't begun
    if game_state == 0:
        return redirect("/lobby")

    # redirect to end screen if game has ended
    if game_state == 2:
        return redirect("/game/end")

    # retrieve all players including their card count
    all_players = cur.execute('''
        SELECT s.position, s.name, s.uno, COUNT(z.complex_deck_id)
        FROM spieler s
        LEFT JOIN kartenzustand z ON s.id = z.ownership
        WHERE s.game_id = ?
        GROUP BY s.id
        ORDER BY s.position ASC
    ''', [ game_id ]).fetchall()

    # retrieve all current players cards
    player_cards = cur.execute('''
        SELECT d.id, t.farbe, t.wert 
        FROM kartenzustand z, complexdeck d, kartentyp t
        WHERE z.ownership = ? AND z.game_id = ? AND
            z.complex_deck_id = d.id AND d.kartentyp_id = t.id
    ''', [ player_id, game_id ]).fetchall()

    # retrieve current card info
    current_card_farbe, current_card_wert = cur.execute('''
        SELECT t.farbe, t.wert
        FROM complexdeck d, kartentyp t
        WHERE d.id = ? AND d.kartentyp_id = t.id
    ''', [ game_current_card_id ]).fetchone()

    def player_cards_with_is_placeable_map(card):
        card_id = card[0]
        card_farbe = card[1]
        card_wert = card[2]

        return (
            card_id, 
            card_farbe, 
            card_wert, 
            can_place_card(
                current_card_farbe = current_card_farbe,
                current_card_wert = current_card_wert,
                card_farbe = card_farbe,
                card_wert = card_wert,
                game_draw_stack = game_draw_stack,
                game_wish_farbe = game_wish_farbe
            )
        )

    player_cards_with_is_placeable = map(player_cards_with_is_placeable_map, player_cards)

    show_uno = False
    game_turn_name = ""

    for player in all_players:
        if game_turn == player[0]:
            game_turn_name = player[1]

        if player[2] == 1:
            show_uno = True

    return render_template(
        "game_complex.html", 
        all_players = all_players,
        player_id = player_id,
        player_position = player_position,
        player_cards = player_cards_with_is_placeable,
        is_players_turn = player_position == game_turn,
        game_turn = game_turn,
        game_turn_name = game_turn_name,
        game_current_card_id = game_current_card_id,
        game_draw_stack = game_draw_stack,
        game_wish_farbe = game_wish_farbe if current_card_farbe == 4 else None,
        current_card_farbe = current_card_farbe,
        current_card_wert = current_card_wert,
        show_uno = show_uno
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

    # retrieve all joined player ids
    all_player_ids = cur.execute('''
        SELECT id FROM spieler WHERE game_id = ?
    ''', [ game_id ]).fetchall()

    # retrieve all available card ids
    all_card_ids = cur.execute('''
        SELECT id FROM complexdeck
    ''').fetchall()

    # shuffle card ids
    random.shuffle(all_card_ids)

    # give each player 7 random cards from complex deck
    for player_id in all_player_ids:
        for i in range(7):
            card_id = all_card_ids.pop()

            cur.execute('''
                INSERT INTO kartenzustand (complex_deck_id, ownership, game_id) VALUES (?, ?, ?)
            ''', [ card_id[0], player_id[0], game_id ])

    # set one random card as current card
    current_card_id = all_card_ids.pop()[0]

    # update game and refresh
    cur.execute('''
        UPDATE game SET 
        deck = ?, 
        state = ?, 
        current_card_id = ?, 
        turn = ?, 
        inverse_direction = ?, 
        refresh = ? 
        WHERE id = ?
    ''', [ 
        1, # deck (1 = complex)
        1, # state (1 = running)
        current_card_id,
        1, # turn
        0, # inverse direction
        round(time.time()), # refresh
        game_id
    ])
    con.commit()

def can_place_card(
        current_card_farbe: int, 
        current_card_wert: int, 
        card_farbe: int, 
        card_wert: int, 
        game_draw_stack: int, 
        game_wish_farbe: int
    ):
    # cannot place black on black
    if current_card_farbe == 4 and card_farbe == 4:
        return False

    # cannot place any card other than +2 when draw_stack > 0
    if game_draw_stack > 0 and (card_wert != 11 or card_farbe == 4):
        return False

    # can place any card of wish color
    if current_card_farbe == 4:
        # cannot put +2 on +4
        if card_wert == 11:
            return False
        return card_farbe == game_wish_farbe

    # allow black cards on all other cards
    if card_farbe == 4:
        return True

    # cannot place when color and value both differ
    if current_card_farbe != card_farbe and current_card_wert != card_wert:
        return False

    return True

def calculate_new_turn(
        con: Connection, 
        cur: Cursor, 
        game_id: int, 
        game_turn: int,
        game_inverse_direction: int
    ):
    if game_inverse_direction == 0:
        new_turn = game_turn + 1
    elif game_inverse_direction == 1: 
        new_turn = game_turn - 1

    max_position = cur.execute('''
        SELECT MAX(position) FROM spieler WHERE game_id = ?
    ''', [ game_id ]).fetchone()[0]

    # handle wrap around
    if new_turn > max_position:
        new_turn = 1
    elif new_turn == 0:
        new_turn = max_position

    return new_turn

def draw_card(
        con: Connection, 
        cur: Cursor, 
        player_position: int, 
        player_id: int,
        player_uno: int, 
        game_id: int
    ):
    # retrieve game info
    game_name, game_deck_id, game_state, game_turn, game_current_card_id, game_draw_stack, game_inverse_direction = cur.execute('''
        SELECT name, deck, state, turn, current_card_id, draw_stack, inverse_direction FROM game WHERE id = ?
    ''', [ game_id ]).fetchone()

    # don't continue if game isn't running
    if game_state != 1:
        return

    # don't continue if it isn't player's turn
    if game_turn != player_position:
        return

    # decide how much cards to draw
    amount = game_draw_stack if game_draw_stack > 0 else 1

    # pick random card out of complexdeck which has no state and isn't the current card
    drawd_card_id = cur.execute('''
        SELECT d.id
        FROM complexdeck d, game g
        LEFT JOIN kartenzustand k ON d.id = k.complex_deck_id
        WHERE k.ownership IS NULL AND d.id != ?
        ORDER BY random()
        LIMIT ?
    ''', [ game_current_card_id, amount ]).fetchall()

    # set card ownership to player_id
    for row in drawd_card_id:
        cur.execute('''
            INSERT INTO kartenzustand (complex_deck_id, ownership, game_id) VALUES (?, ?, ?)
        ''', [ row[0], player_id, game_id ])
    
    # reset player's uno value
    if player_uno == 1:
        cur.execute('''
            UPDATE spieler SET uno = 0 WHERE id = ?
        ''', [ player_id ])

    #  update game and refresh
    cur.execute('''
        UPDATE game SET 
        turn = ?, 
        draw_stack = 0, 
        refresh = ? 
        WHERE id = ?
    ''', [ 
        calculate_new_turn(
            con = con, 
            cur = cur, 
            game_id = game_id, 
            game_turn = game_turn,
            game_inverse_direction = game_inverse_direction
        ), 
        round(time.time()), 
        game_id 
    ])
    con.commit()

def place_card(con: Connection, cur: Cursor, player_position: int, player_id: int, player_uno: int, game_id: int, card_id: int, new_wish_farbe: int):
    game_name, game_deck_id, game_state, game_turn, game_current_card_id, game_draw_stack, game_inverse_direction, game_wish_farbe = cur.execute('''
        SELECT name, deck, state, turn, current_card_id, draw_stack, inverse_direction, wish_farbe FROM game WHERE id = ?
    ''', [ game_id ]).fetchone()

    # don't continue if game isn't running
    if game_state != 1:
        return

    # don't continue if it isn't player's turn
    if game_turn != player_position:
        return
    
    player_count = cur.execute('''
        SELECT COUNT(id) FROM spieler WHERE game_id = ?
    ''', [ game_id ]).fetchone()[0]

    # retrieve current card info
    current_card_farbe, current_card_wert = cur.execute('''
        SELECT t.farbe, t.wert
        FROM complexdeck d, kartentyp t
        WHERE d.id = ? AND d.kartentyp_id = t.id
    ''', [ game_current_card_id ]).fetchone()

    # retrieve placing card info
    card_farbe, card_wert = cur.execute('''
        SELECT t.farbe, t.wert
        FROM complexdeck d, kartentyp t
        WHERE d.id = ? AND d.kartentyp_id = t.id
    ''', [ card_id ]).fetchone()

    # abort if card is not placeable
    if not can_place_card(
        current_card_farbe = current_card_farbe,
        current_card_wert = current_card_wert,
        card_farbe = card_farbe,
        card_wert = card_wert,
        game_draw_stack = game_draw_stack,
        game_wish_farbe = game_wish_farbe,
    ):
        return

    # card can be placed

    # ***** Special Card Effects *****

    # Wünschekarten
    if card_farbe == 4:
        if new_wish_farbe is None:
            return

        game_wish_farbe = new_wish_farbe
        
        # draw_stack erhöhen bei +4
        if card_wert == 14:
            game_draw_stack += 4

    # Richtungswechsel: toggles inverse_direction betwenn 0 and 1 
    elif card_wert == 10:
        game_inverse_direction = not game_inverse_direction

        # Richtungswechsel is like Aussetzen if player count = 2
        if player_count == 2:
            # skip one player
            game_turn = calculate_new_turn(
                con = con, 
                cur = cur, 
                game_id = game_id, 
                game_turn = game_turn,
                game_inverse_direction = game_inverse_direction
            )

    # +2 (draw_stack wird erhöht)
    elif card_wert == 11:
        game_draw_stack += 2
    
    # Aussetze Karte
    elif card_wert == 12:
        # skip one player
        game_turn = calculate_new_turn(
            con = con, 
            cur = cur, 
            game_id = game_id, 
            game_turn = game_turn,
            game_inverse_direction = game_inverse_direction
        )
    
    # determine next game_turn value
    game_turn = calculate_new_turn(
        con = con, 
        cur = cur,
        game_id = game_id, 
        game_turn = game_turn,
        game_inverse_direction = game_inverse_direction
    )

    # ***** Winner Check *****
    # retrieve card count of player
    player_card_count = cur.execute('''
        SELECT COUNT(complex_deck_id) FROM kartenzustand
        WHERE game_id = ? AND ownership = ?
    ''', [ game_id, player_id ]).fetchone()[0]

    # if card count = 1, player has won
    if player_card_count == 1:
        cur.execute('''
            UPDATE game SET state = 2, winner = ?, refresh = ? WHERE id = ?
        ''', [ player_id, round(time.time()), game_id ])
        con.commit()
        return

    # reset players uno value
    if player_card_count == 2:
        cur.execute('''
            UPDATE spieler SET uno = 1 WHERE id = ?
        ''', [ player_id ])
    elif player_uno == 1:
        cur.execute('''
            UPDATE spieler SET uno = 0 WHERE id = ?
        ''', [ player_id ])

    # update game and refresh
    cur.execute('''
        UPDATE game SET 
        current_card_id = ?, 
        turn = ?,
        draw_stack = ?,
        inverse_direction = ?,
        wish_farbe = ?,
        refresh = ? 
        WHERE id = ?
    ''', [ 
        card_id, 
        game_turn, 
        game_draw_stack,
        game_inverse_direction,
        game_wish_farbe,
        round(time.time()), 
        game_id 
    ])

    # revoke card ownership from player by deleting kartenzustand
    cur.execute('''
        DELETE FROM kartenzustand WHERE complex_deck_id = ? AND ownership = ? AND game_id = ?
    ''', [ card_id, player_id, game_id ])
    con.commit()

def uno(con: Connection, cur: Cursor, player_id: int, player_uno: int, game_id: int):
    game_state, game_current_card_id = cur.execute('''
        SELECT state, current_card_id FROM game WHERE id = ?
    ''', [ game_id ]).fetchone()

    # don't continue if game isn't running
    if game_state != 1:
        return

    # refresh game
    cur.execute('''
        UPDATE game SET refresh = ? WHERE id = ?
    ''', [
        round(time.time()), 
        game_id 
    ])

    # player is affected by uno
    if player_uno == 1:
        # reset uno state
        cur.execute('''
            UPDATE spieler SET uno = 0 WHERE id = ?
        ''', [ player_id ])
        con.commit()
        return

    # all players with uno = 1 draw two cards
    uno_player_ids = cur.execute('''
        SELECT id FROM spieler WHERE uno = 1
    ''').fetchall()
    
    # get random, unused card ids
    all_card_ids = cur.execute('''
        SELECT d.id
        FROM complexdeck d, game g
        LEFT JOIN kartenzustand k ON d.id = k.complex_deck_id
        WHERE k.ownership IS NULL AND d.id != ?
        ORDER BY random()
    ''', [ game_current_card_id ]).fetchall()

    # give each uno_player two cards
    for player_id in uno_player_ids:
        for i in range(2):
            card_id = all_card_ids.pop()

            # set card ownership to player_id
            cur.execute('''
                INSERT INTO kartenzustand (complex_deck_id, ownership, game_id) VALUES (?, ?, ?)
            ''', [ card_id[0], player_id[0], game_id ])

        cur.execute('''
            UPDATE spieler SET uno = 0 WHERE id = ?
        ''', [ player_id[0] ])
    
    con.commit()