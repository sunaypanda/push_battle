import numpy as np
import requests
import time
from PushBattle import Game, PLAYER1, PLAYER2, EMPTY, BOARD_SIZE, NUM_PIECES, _torus, chess_notation_to_array, array_to_chess_notation
import random

TIMEOUT = 4  # timeout for each move in seconds

class RandomAgent:
    def __init__(self, player=PLAYER1):
        self.player = player

    def get_possible_moves(self, game):
        moves = []
        current_pieces = game.p1_pieces if game.current_player == PLAYER1 else game.p2_pieces

        if current_pieces < NUM_PIECES:
            for r in range(BOARD_SIZE):
                for c in range(BOARD_SIZE):
                    if game.board[r][c] == EMPTY:
                        moves.append((r, c))
        else:
            for r0 in range(BOARD_SIZE):
                for c0 in range(BOARD_SIZE):
                    if game.board[r0][c0] == game.current_player:
                        for r1 in range(BOARD_SIZE):
                            for c1 in range(BOARD_SIZE):
                                if game.board[r1][c1] == EMPTY:
                                    moves.append((r0, c0, r1, c1))
        return moves

    def get_best_move(self, game):
        possible_moves = self.get_possible_moves(game)
        return random.choice(possible_moves)


class Agent:
    def __init__(self, participant, agent_name, latency=None):
        self.participant = participant
        self.agent_name = agent_name
        self.latency = latency


class Judge:
    def __init__(self, p1_url, p2_url):
        self.p1_url = p1_url
        self.p2_url = p2_url
        self.game = Game()
        self.p1_agent = None
        self.p2_agent = None
        self.game_str = ""

    def check_latency(self):
        try:
            start_time = time.time()
            response = requests.get(self.p1_url, timeout=TIMEOUT)
            response.raise_for_status()
            self.p1_agent = Agent("Participant1", "Agent1", time.time() - start_time)
            print(f"Connected to Player 1 with latency {self.p1_agent.latency:.3f}s")
        except requests.RequestException as e:
            print(f"Failed to connect to Player 1: {e}")
            return False

        try:
            start_time = time.time()
            response = requests.get(self.p2_url, timeout=TIMEOUT)
            response.raise_for_status()
            self.p2_agent = Agent("Participant2", "Agent2", time.time() - start_time)
            print(f"Connected to Player 2 with latency {self.p2_agent.latency:.3f}s")
        except requests.RequestException as e:
            print(f"Failed to connect to Player 2: {e}")
            return False

        return True

    def start_game(self):
        starting_data = {
            "game": self.game.to_dict(),
            "board": self.game.board.tolist(),
            "max_latency": TIMEOUT,
        }
        try:
            starting_data['first_turn'] = True
            response = requests.post(f"{self.p1_url}/start", json=starting_data, timeout=TIMEOUT)
            response.raise_for_status()
            print("Game started for Player 1")
        except requests.RequestException as e:
            print(f"Failed to start game for Player 1: {e}")
            return False

        try:
            starting_data['first_turn'] = False
            response = requests.post(f"{self.p2_url}/start", json=starting_data, timeout=TIMEOUT)
            response.raise_for_status()
            print("Game started for Player 2")
            return True
        except requests.RequestException as e:
            print(f"Failed to start game for Player 2: {e}")
            return False

    def receive_move(self, attempt_number, p1_random, p2_random):
        move_data = {
            "game": self.game.to_dict(),
            "board": self.game.board.tolist(),
            "turn_count": self.game.turn_count,
            "attempt_number": attempt_number,
        }
        try:
            if self.game.current_player == PLAYER1:
                move_data["random_attempts"] = p1_random
                start_time = time.time()
                response = requests.post(f"{self.p1_url}/move", json=move_data, timeout=TIMEOUT)
                response.raise_for_status()
                end_time = time.time()
                self.p1_agent.latency = (end_time - start_time)
            else:
                move_data["random_attempts"] = p2_random
                start_time = time.time()
                response = requests.post(f"{self.p2_url}/move", json=move_data, timeout=TIMEOUT)
                response.raise_for_status()
                end_time = time.time()
                self.p2_agent.latency = (end_time - start_time)

            move = response.json()
            handled_move = self.handle_move(self.game, move['move'])

            if handled_move == "forfeit":
                return "forfeit"
            elif handled_move:
                return True
            else:
                return False
        except (requests.RequestException, requests.Timeout) as e:
            print(f"Failed to receive move: {e}")
            return False

    def end_game(self, winner):
        end_data = {
            "game": self.game.to_dict(),
            "board": self.game.board.tolist(),
            "turn_count": self.game.turn_count,
            "winner": int(winner)
        }
        try:
            requests.post(f"{self.p1_url}/end", json=end_data, timeout=TIMEOUT)
            requests.post(f"{self.p2_url}/end", json=end_data, timeout=TIMEOUT)
            print(f"Winner: {'PLAYER1' if winner == PLAYER1 else 'PLAYER2'}")
        except requests.RequestException as e:
            print(f"Failed to send end game data: {e}")

    def handle_move(self, game, move):
        if not isinstance(move, (list, tuple)) or len(move) not in [2, 4]:
            print(f"Invalid move format by Player {'P1' if game.current_player == PLAYER1 else 'P2'}")
            return "forfeit"

        chess_move = array_to_chess_notation(move)
        print(f"{game.current_player}'s move is: {move} or {chess_move}")

        move = [int(x) for x in move]

        if game.turn_count < 17:
            if game.is_valid_placement(move[0], move[1]):
                game.place_checker(move[0], move[1])
            else:
                print(f"Invalid placement by {game.current_player}")
                return "forfeit"
        else:
            if game.is_valid_move(move[0], move[1], move[2], move[3]):
                game.move_checker(move[0], move[1], move[2], move[3])
            else:
                print(f"Invalid move by {game.current_player}")
                return "forfeit"

        self.game_str += f"-{chess_move}"
        return True


def main():
    print("Creating judge...")
    judge = Judge("http://127.0.0.1:5009", "http://127.0.0.1:5008")

    if not judge.check_latency():
        print("Failed to connect to one or both players")
        return

    print(f"Player 1: {judge.p1_agent.agent_name} ({judge.p1_agent.participant})")
    print(f"Player 2: {judge.p2_agent.agent_name} ({judge.p2_agent.participant})")
    print(f"Initial latencies - P1: {judge.p1_agent.latency:.3f}s, P2: {judge.p2_agent.latency:.3f}s")

    print("Starting game...")
    if not judge.start_game():
        print("Failed to start game")
        return

    p1_random = 5
    p2_random = 5

    while True:
        judge.game.turn_count += 1
        print(f"Turn {judge.game.turn_count}")
        print("Sending move to:", judge.game.current_player)

        print("First move attempt")
        first_attempt = judge.receive_move(1, p1_random, p2_random)

        if first_attempt == "forfeit":
            winner = PLAYER2 if judge.game.current_player == PLAYER1 else PLAYER1
            judge.end_game(winner)
            print("Game String:", judge.game_str)
            break

        if not first_attempt:
            print("Second move attempt")
            second_attempt = judge.receive_move(2, p1_random, p2_random)
            if second_attempt == "forfeit":
                winner = PLAYER2 if judge.game.current_player == PLAYER1 else PLAYER1
                judge.end_game(winner)
                print("Game String:", judge.game_str)
                break

            if not second_attempt:
                print(f"Player {'PLAYER1' if judge.game.current_player == PLAYER1 else 'PLAYER2'} failed to make a valid move.")
                current_random_moves = p1_random if judge.game.current_player == PLAYER1 else p2_random
                if current_random_moves > 0:
                    random_agent = RandomAgent(player=judge.game.current_player)
                    move = random_agent.get_best_move(judge.game)
                    judge.handle_move(judge.game, move)
                    judge.game_str += 'r'
                    if judge.game.current_player == PLAYER1:
                        p1_random -= 1
                        print(f"P1 has {p1_random} random moves left")
                    else:
                        p2_random -= 1
                        print(f"P2 has {p2_random} random moves left")
                else:
                    winner = PLAYER2 if judge.game.current_player == PLAYER1 else PLAYER1
                    judge.end_game(winner)
                    judge.game_str += "-q"
                    print("Game String:", judge.game_str)
                    break

        judge.game.display_board()
        winner = judge.game.check_winner()
        if winner != EMPTY:
            judge.end_game(winner)
            print("Game String:", judge.game_str)
            break

        judge.game.current_player *= -1
        print()

if __name__ == "__main__":
    main()
