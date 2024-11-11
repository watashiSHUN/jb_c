import random
from collections import Counter
from enum import Enum

from fastapi import WebSocket


class Player:
    def __init__(self, player_id: str, websocket: WebSocket, game):
        # player property
        self.player_id = player_id
        self.websocket = websocket
        self.score = 0
        self.is_host = False
        self.game = game

    async def send_message(self, message: str):
        await self.websocket.send_text(message)

    async def read_message(self) -> str:
        return await self.websocket.receive_text()

    def set_host(self):
        self.is_host = True

    # player thread
    async def play(self):
        while True:
            # check game state
            user_input = await self.read_message()
            await self.send_message(f"user_input: {user_input}")  # echo
            if (
                self.is_host
                and self.game.state == GameState.WAITING_FOR_NEW_PLAYERS
                and user_input == "START"
            ):
                await self.game.start()
            elif self.game.state == GameState.WAITING_FOR_PLAYER_INPUT:
                await self.game.submit_answer(self.player_id, user_input)
            elif self.game.state == GameState.WAITING_FOR_PLAYER_VOTE:
                await self.game.register_vote(self.player_id, int(user_input))


class GameState(Enum):
    WAITING_FOR_NEW_PLAYERS = 1
    WAITING_FOR_PLAYER_INPUT = 2
    WAITING_FOR_PLAYER_VOTE = 3
    ROUND_FINISH = 4


class Game:
    def __init__(self):
        self.players = {}  # player_id -> Player
        self.host = None
        self.state = GameState.WAITING_FOR_NEW_PLAYERS
        self.prompt = "What is your favorite color?"
        self.player_answers = {}  # player_id -> answer
        self.shuffled_order = []  # shuffled player_id
        self.player_votes = {}  # player_id -> vote given, NOT vote received
        # TODO(shunxian) ai implementation
        self.ai_answers = {}  # ai(different ai implementation?) -> answer

    async def add_player(self, player: Player):
        await player.websocket.accept()
        # broadcast user joined
        await self.broadcast(f"Client #{player.player_id} joined the room")
        self.players[player.player_id] = player

        if self.host is None:
            self.host = player
            player.set_host()
            await player.send_message(
                "You are the host, once you are ready, type 'START'"
            )

    async def remove_player(self, player):
        del self.players[player.player_id]
        # broadcast user left
        await self.broadcast(f"Client #{player.player_id} left the room")

    async def broadcast(self, message: str):
        # TODO(shunxian): replace this with spectator
        for player in self.players.values():
            await player.send_message(message)

    # TODO(shunxian): this doesn't need to be async?
    # `start()` should not block host
    async def start(self):
        self.state = GameState.WAITING_FOR_PLAYER_INPUT
        await self.broadcast(
            f"Game started, Question is {self.prompt} waiting for player input"
        )

    async def submit_answer(self, player_id: str, answer: str):
        self.player_answers[player_id] = answer
        if len(self.player_answers) == len(self.players):
            # all player has submitted their answer, randomize the order and wait for user vote
            self.state = GameState.WAITING_FOR_PLAYER_VOTE
            self.shuffle_answers()
            for i, player_id in enumerate(self.shuffled_order):
                await self.broadcast(f"{i+1}: {self.player_answers[player_id]}")
            await self.broadcast("Please vote for the best answer")

    # TODO(shunxian): cannot vote for yourself
    async def register_vote(self, player_id: str, vote: int):
        self.player_votes[player_id] = vote
        if len(self.player_votes) == len(self.players):
            # all player has voted, calculate the winner
            self.state = GameState.ROUND_FINISH
            winner = self.compute_winner()
            await self.broadcast(f"winner is {winner}, Round finish")

    def compute_winner(self) -> int:
        Counter(self.player_votes.values())
        highest_vote = -1
        higest_occ = 0
        # TODO(shunxian): draw
        for vote, occ in Counter(self.player_votes.values()).items():
            if occ > higest_occ:
                highest_vote = vote
                higest_occ = occ
        return self.shuffled_order[highest_vote - 1]

    def shuffle_answers(self):
        # shuffle player_id
        players = list(self.player_answers.keys())
        # random.shuffle(players)
        for i in range(len(players)):
            # swap i with i...len()-1
            to_swap = random.randint(i, len(players) - 1)
            players[i], players[to_swap] = players[to_swap], players[i]
        self.shuffled_order = players
