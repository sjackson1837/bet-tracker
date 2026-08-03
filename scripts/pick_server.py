"""
Tiny local HTTP server that lets the static site (site/index.html) mark which
games you actually bet on with a checkbox click, instead of telling Claude in
chat. Run this on your machine while you're browsing the site:

    python3 scripts/pick_server.py

(Or double-click scripts/start_pick_server.command on a Mac.) Leave it running
in a terminal tab / background while you click checkboxes on the site.

It only listens on 127.0.0.1 (your machine only, never the network) and does
two things whenever a checkbox is toggled:
  1. Flips "user_selected" on that game in data/games.json -- the same field
     scripts/mark_picks.py sets when you tell Claude which teams you bet on.
  2. Rebuilds the site so results.html's "Your picks" record and the
     checkmark badge on index.html stay in sync immediately.

No API key, no external network access -- this is a pure local file server,
so it can safely run alongside (or instead of) the chat-based mark_picks.py
workflow.
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import build_site
from games_store import load_games, save_games

PORT = 8934


class Handler(BaseHTTPRequestHandler):
    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self._cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "ok"})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/toggle-pick":
            self._send_json(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            game_id = body["game_id"]
        except Exception:
            self._send_json(400, {"error": "expected JSON body with game_id"})
            return

        games = load_games()
        game = games.get(game_id)
        if game is None:
            self._send_json(404, {"error": f"unknown game_id {game_id}"})
            return

        game["user_selected"] = not game.get("user_selected", False)
        save_games(games)
        build_site.main()  # keep index.html/results.html in sync immediately

        self._send_json(200, {
            "game_id": game_id,
            "user_selected": game["user_selected"],
        })

    def log_message(self, fmt, *args):
        print(f"[pick_server] {self.address_string()} - {fmt % args}")


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Pick server running at http://127.0.0.1:{PORT} (Ctrl+C to stop)")
    print("Leave this running while you browse site/index.html to mark picks.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
