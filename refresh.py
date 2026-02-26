from flask import request, session
import time

def refresh(con, cur, game_id):
    cur.execute("UPDATE game SET refresh = ? WHERE id = ?", [ round(time.time()), game_id ])
    con.commit()

def get_refresh(con, cur, game_id):
    res = cur.execute("SELECT refresh FROM game WHERE id = ?", [ game_id ]).fetchone()
    return str(res)

def handle_refresh(con, cur):
    if not "game_id" in session:
        return ""

    game_id = session["game_id"]
    return get_refresh(con, cur, game_id)