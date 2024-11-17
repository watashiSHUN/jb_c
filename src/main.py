import os
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

import entity

app = FastAPI()

# TODO(shunxian): to be replaced
html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Jackbox Clone</title>
    </head>
    <body>
        <h2>Your ID (currently auto generated): <span id="ws-id"></span></h2>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var client_id = Date.now()
            document.querySelector("#ws-id").textContent = client_id;
            var ws = new WebSocket(`SERVER_ADDRESS/ws/${client_id}`);
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode("server message: " + event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""
host_port = os.environ.get("PORT", 8080)
service_name = os.environ.get("K_SERVICE", None)
print("DEBUG service_name:", service_name)
# user specified environment variables
project_number = os.environ.get("PROJECT_NUMBER", None)
region = os.environ.get("REGION", None)
host = "ws://localhost"  # protocol and host

if service_name is not None:
    host = f"wss://{service_name}-{project_number}.{region}.run.app"

# Get deterministic URL
# https://cloud.google.com/run/docs/triggering/https-request#deterministic
host_address = ":".join([host, str(host_port)])

html = html.replace("SERVER_ADDRESS", host_address)
game = entity.Game()


# return a web page that initiate a websocket
@app.get("/")
async def get():
    return HTMLResponse(html)


@app.websocket("/ws/{player_id}")
async def websocket_endpoint(websocket: WebSocket, player_id: str):
    if game.state != entity.GameState.WAITING_FOR_NEW_PLAYERS:
        await websocket.send_text("Game already started")
        return

    player = entity.Player(player_id, websocket, game)
    # TODO(shunxian): thread safety? multiple player joining the game at the same time?
    await game.add_player(player)
    try:
        await player.play()
    except WebSocketDisconnect:
        await game.remove_player(player)


if __name__ == "__main__":
    import uvicorn

    print("DEBUG hosting message:", host_address)
    uvicorn.run(app, host="0.0.0.0", port=int(host_port))