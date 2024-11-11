from typing import Any

import entity
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

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
            var ws = new WebSocket(`ws://localhost:8000/ws/${client_id}`);
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
