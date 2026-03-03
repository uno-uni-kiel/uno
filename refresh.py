from flask import request, session
import time

def handle_refresh(con, cur):
    if not "game_id" in session:
        return ""

    game_id = session["game_id"]
    res = cur.execute("SELECT refresh FROM game WHERE id = ?", [ game_id ]).fetchone()
    return str(res)