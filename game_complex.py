from flask import Request, render_template, request, session, redirect
from sqlite3 import Connection, Cursor

import time
import random

def handle_game_complex(con: Connection, cur: Cursor):
    if not "spieler_id" in session:
        return redirect("/")

    player_id = session["spieler_id"]
    player_position, game_id = cur.execute('''
        SELECT position, game_id FROM spieler WHERE id = ?
    ''', [ player_id ]).fetchone()

    # redirect if player isn't in any game
    if not game_id:
        return redirect("/create_or_join")

    wish_farbe = cur.execute('''
        SELECT wish_farbe FROM game WHERE id = ?
    ''', [ game_id ]).fetchone()[0]

    # actions
    if request.method == "POST":
        # draw a card
        if request.form["type"] == "draw":
            draw_card(con, cur, player_position, player_id, game_id)
        # place a card
        elif request.form["type"] == "place_card":
            new_wish_farbe = request.form.get("wish_farbe")  
            if new_wish_farbe is not None:
                wish_farbe = int(new_wish_farbe)
                cur.execute('''
                    UPDATE game SET wish_farbe = ? WHERE id = ?
                ''', [ wish_farbe, game_id ])
                con.commit()
            
            place_card(con, cur, player_position, player_id, game_id, request.form["card_id"], new_wish_farbe)

    # retrieve game info
    game_name, game_deck_id, game_state, game_turn, game_current_card_id = cur.execute('''
        SELECT name, deck, state, turn, current_card_id FROM game WHERE id = ?
    ''', [ game_id ]).fetchone()

    is_players_turn = player_position == game_turn

    # redirect to lobby if game hasn't begun
    if game_state == 0:
        return redirect("/lobby")

    # redirect to end screen if game has ended
    if game_state == 2:
        return redirect("/game/end")

    # retrieve all players including their card count
    all_players = cur.execute('''
        SELECT s.position, s.name, COUNT(z.complex_deck_id)
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

    current_card_is_draw_two = current_card_wert == 11

    # calculate brightness class for each card
    player_cards_with_brightness = []
    for card_id, card_farbe, card_wert in player_cards:
        if not is_players_turn:
            player_cards_with_brightness.append(
                (card_id, card_farbe, card_wert, "brightness-50")
            )
            continue

        is_not_placeable = current_card_farbe != card_farbe and current_card_wert != card_wert
        card_is_draw_two = card_wert == 11
        
        if is_not_placeable or (current_card_is_draw_two and not card_is_draw_two):
            player_cards_with_brightness.append(
                (card_id, card_farbe, card_wert, "brightness-70")
            )
            continue

        player_cards_with_brightness.append(
            (card_id, card_farbe, card_wert, "brightness-100")
        )

    return render_template(
        "game_complex.html", 
        all_players = all_players,
        player_id = player_id,
        player_position = player_position,
        player_cards = player_cards_with_brightness,
        game_turn = game_turn,
        game_current_card_id = game_current_card_id,
        current_card_farbe = current_card_farbe,
        current_card_wert = current_card_wert,
        wish_farbe = wish_farbe if current_card_farbe == 4 else None
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

    cur.execute('''
        UPDATE game SET deck = ?, state = ?, current_card_id = ?, turn = ?, inverse_direction = ?, refresh = ? WHERE id = ?
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

def calculate_new_turn(con: Connection, cur: Cursor, game_id: int, game_turn):
    inverse = cur.execute('''
        SELECT inverse_direction FROM game WHERE id = ?
    ''', [ game_id ]).fetchone()[0]
    
    if inverse == 0:
        new_turn = game_turn + 1
    elif inverse == 1: 
        new_turn = game_turn - 1
    new_turn_player = cur.execute('''
        SELECT 1 FROM spieler WHERE game_id = ? AND position = ? LIMIT 1
    ''', [ game_id, new_turn ]).fetchone()
            
    max_position = cur.execute('''
        SELECT MAX(position) FROM spieler WHERE game_id = ?
    ''', [ game_id ]).fetchone()[0]

    # handle wrap around
    if new_turn > max_position:
        new_turn = 1
    elif new_turn == 0:
        new_turn = max_position

    return new_turn

def draw_card(con: Connection, cur: Cursor, player_position: int, player_id: int, game_id: int):
    game_name, game_deck_id, game_state, game_turn, game_current_card_id = cur.execute('''
        SELECT name, deck, state, turn, current_card_id FROM game WHERE id = ?
    ''', [ game_id ]).fetchone()

    # don't continue if game isn't running
    if game_state != 1:
        return

    # don't continue if it isn't player's turn
    if game_turn != player_position:
        return

    # retrieve draw_stack
    draw_stack = cur.execute('''
        SELECT draw_stack FROM game WHERE id = ?
    ''', [ game_id ]).fetchone()[0]

    # decide how much cards to draw
    if draw_stack > 0:
        amount = draw_stack
    else:
        amount = 1

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
    
    # draw_stack zurücksetzen
    if draw_stack > 0:
        cur.execute('''
            UPDATE game SET draw_stack = 0 WHERE id = ? 
        ''', [ game_id ])

    # new turn and refresh game
    cur.execute('''
        UPDATE game SET turn = ?, refresh = ? WHERE id = ?
    ''', [ 
        calculate_new_turn(con, cur, game_id, game_turn), 
        round(time.time()), 
        game_id 
    ])
    con.commit()

def place_card(con: Connection, cur: Cursor, player_position: int, player_id: int, game_id: int, card_id: int, wish_farbe: int):
    game_name, game_deck_id, game_state, game_turn, game_current_card_id = cur.execute('''
        SELECT name, deck, state, turn, current_card_id FROM game WHERE id = ?
    ''', [ game_id ]).fetchone()

    # don't continue if game isn't running
    if game_state != 1:
        return

    # don't continue if it isn't player's turn
    if game_turn != player_position:
        return


    # retrieve current card info
    current_card_farbe, current_card_wert = cur.execute('''
        SELECT t.farbe, t.wert
        FROM complexdeck d, kartentyp t, game g
        WHERE d.id = ? AND d.kartentyp_id = t.id
    ''', [ game_current_card_id ]).fetchone()


    # retrieve placing card info
    card_farbe, card_wert = cur.execute('''
        SELECT t.farbe, t.wert
        FROM complexdeck d, kartentyp t
        WHERE d.id = ? AND d.kartentyp_id = t.id
    ''', [ card_id ]).fetchone()

    db_wish_farbe = cur.execute('''
        SELECT wish_farbe FROM game WHERE id = ?
    ''', [ game_id ]).fetchone()[0]

    if current_card_farbe == 4 and db_wish_farbe is not None:
        current_card_farbe = db_wish_farbe

    # don't continue if neither card color or card value match, when draw_stack > 0 only +2 can be placed
    draw_stack = cur.execute('''
        SELECT draw_stack FROM game WHERE id = ?    
    ''', [ game_id ]).fetchone()[0]
    if card_farbe != 4:
        if draw_stack > 0 and card_wert != 11:
            return
        if draw_stack == 0 and current_card_farbe != card_farbe and current_card_wert != card_wert:
            return
    
    if current_card_farbe == 4 and card_farbe == 4:
        return

    # handle wish color logic
    if card_farbe == 4:
        if wish_farbe is None:
            return
        # draw_stack erhöhen bei +4
        if card_wert == 14:
            cur.execute('''
                UPDATE game SET draw_stack = draw_stack + 4 WHERE id = ?
            ''', [ game_id] )
        
        new_turn = calculate_new_turn(con, cur, game_id, game_turn)

        cur.execute('''
            UPDATE game
            SET current_card_id = ?, 
                wish_farbe = ?, 
                turn = ?, 
                refresh = ?
            WHERE id = ?
        ''', [ card_id, wish_farbe, new_turn, round(time.time()), game_id ])

        cur.execute('''
            DELETE FROM kartenzustand
            WHERE complex_deck_id = ? AND ownership = ? AND game_id = ?
        ''', [card_id, player_id, game_id])

        con.commit()
        return

    # card can be placed

    # ***** Special Card Effects *****

    # Richtungswechsel: toggles inverse_direction betwenn 0 and 1 
    if card_wert == 10:
        inverse = cur.execute('''
            SELECT inverse_direction FROM game WHERE id = ?
        ''', [ game_id ]).fetchone()[0]
        inverse = 1 - inverse
        cur.execute('''
            UPDATE game SET inverse_direction = ? WHERE id = ?
        ''', [ inverse, game_id ])

    # +2 (draw_stack wird erhöht)
    elif card_wert == 11:
        cur.execute('''
            UPDATE game SET draw_stack = draw_stack + 2 WHERE id = ?
        ''', [ game_id ])
    

    # Aussetze Karte
    if card_wert == 12:
        skipped_turn = calculate_new_turn(con, cur, game_id, game_turn)
        game_turn = calculate_new_turn(con, cur, game_id, skipped_turn)
    else:
        game_turn = calculate_new_turn(con, cur, game_id, game_turn)        

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

    # set current_card_id to card_id, set new turn value and update refresh value
    cur.execute('''
        UPDATE game SET current_card_id = ?, turn = ?, refresh = ? WHERE id = ?
    ''', [ 
        card_id, 
        game_turn, 
        round(time.time()), 
        game_id 
    ])
    # delete kartenzustand
    cur.execute('''
        DELETE FROM kartenzustand WHERE complex_deck_id = ? AND ownership = ? AND game_id = ?
    ''', [ card_id, player_id, game_id ])
    con.commit()