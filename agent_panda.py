import random
import json
import os
from PushBattle import Game, PLAYER1, PLAYER2, EMPTY, BOARD_SIZE

class MonteCarloAgent:
    def __init__(self, player=PLAYER1):
        self.player = player
        self.move_scores = {}
        self.win_count = 0
        self.total_games = 0
        self.total_move_score = 0
        self.prev_win_rate = 0.0
        self.game_moves = []
        self.turns_in_game = 0
        self.offensive_moves = 0
        self.defensive_moves = 0
        self.offensive_weight = 5
        self.defensive_weight = 5

    def evaluate_move(self, move, game):
        """Evaluates and scores a move, tracking it as offensive or defensive."""
        move_key = str(move)
        move_score = self.move_scores.get(move_key, 1)
        
        # Track if the move is offensive or defensive
        if self.is_offensive_move(move, game):
            self.offensive_moves += 1
            move_score += self.offensive_weight  # Adaptive score for offensive moves
        elif self.is_defensive_move(move, game):
            self.defensive_moves += 1
            move_score += self.defensive_weight  # Adaptive score for defensive moves

        return move_score

    def update_move_scores(self, winning_moves):
        """Increases scores for moves that contributed to a win."""
        for move in winning_moves:
            move_key = str(move)
            if move_key in self.move_scores:
                self.move_scores[move_key] += 5
            else:
                self.move_scores[move_key] = 5

    def get_possible_moves(self, game):
        """Generate all possible moves for the current state."""
        moves = []
        current_pieces = game.p1_pieces if self.player == PLAYER1 else game.p2_pieces

        if current_pieces < 8:   # Placement phase
            for r in range(BOARD_SIZE):
                for c in range(BOARD_SIZE):
                    if game.board[r][c] == EMPTY:
                        moves.append([r, c])  # Use list instead of tuple
        else:   # Movement phase
            for r0 in range(BOARD_SIZE):
                for c0 in range(BOARD_SIZE):
                    if game.board[r0][c0] == self.player:
                        for r1 in range(BOARD_SIZE):
                            for c1 in range(BOARD_SIZE):
                                if game.board[r1][c1] == EMPTY:
                                    moves.append([r0, c0, r1, c1])  # Use list instead of tuple
        return moves

    def get_best_move(self, game):
        """Selects the best move, prioritizing offensive and defensive moves."""
        possible_moves = self.get_possible_moves(game)
        ordered_moves = self.order_moves(possible_moves)  # Ordering to prioritize center and corners
        scored_moves = [(move, self.evaluate_move(move, game)) for move in ordered_moves]
        
        best_move, best_score = max(scored_moves, key=lambda x: x[1])
        self.total_move_score += best_score
        self.game_moves.append(best_move)
        self.turns_in_game += 1
        return best_move

    def is_offensive_move(self, move, game):
        """Check if the move helps create a winning line of three for the player."""
        r, c = (move if len(move) == 2 else move[2:4])  # Target row, column for placement or movement
        return self.check_for_line(r, c, self.player, game)

    def is_defensive_move(self, move, game):
        """Check if the move prevents the opponent from getting three in a row."""
        r, c = (move if len(move) == 2 else move[2:4])  # Target row, column for placement or movement
        opponent = PLAYER2 if self.player == PLAYER1 else PLAYER1
        return self.check_for_line(r, c, opponent, game)

    def check_for_line(self, r, c, player, game):
        """Helper function to check if placing/moving a piece at (r, c) creates or blocks three in a row."""
        directions = [(1, 0), (0, 1), (1, 1), (1, -1)]  # Vertical, horizontal, and both diagonals

        for dr, dc in directions:
            count = 1  # Start with the piece being placed/moved

            # Check in the negative direction
            nr, nc = r - dr, c - dc
            while 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and game.board[nr][nc] == player:
                count += 1
                nr -= dr
                nc -= dc

            # Check in the positive direction
            nr, nc = r + dr, c + dc
            while 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and game.board[nr][nc] == player:
                count += 1
                nr += dr
                nc += dc

            # If we find three or more in a row, this move is offensive or defensive
            if count >= 3:
                return True

        return False

    def order_moves(self, moves):
        """Sort moves to prioritize center and corners for strategic advantage."""
        center = (BOARD_SIZE // 2, BOARD_SIZE // 2)
        corners = [(0, 0), (0, BOARD_SIZE - 1), (BOARD_SIZE - 1, 0), (BOARD_SIZE - 1, BOARD_SIZE - 1)]
        
        return sorted(moves, key=lambda move: (
            move == center,  # Prioritize center
            move in corners,  # Prioritize corners
        ), reverse=True)

    def reset_game_stats(self):
        """Resets stats specific to each game."""
        self.turns_in_game = 0
        self.offensive_moves = 0
        self.defensive_moves = 0
        self.game_moves = []

    def save_agent(self, filename='agent_data.json'):
        """Saves agent's learning data to a JSON file."""
        data = {
            'move_scores': self.move_scores,
            'win_count': self.win_count,
            'total_games': self.total_games,
            'total_move_score': self.total_move_score
        }
        with open(filename, 'w') as f:
            json.dump(data, f)

    def load_agent(self, filename='agent_data.json'):
        """Loads agent's learning data from a JSON file and adjusts strategy based on past data."""
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                data = json.load(f)
                self.move_scores = data.get('move_scores', {})
                self.win_count = data.get('win_count', 0)
                self.total_games = data.get('total_games', 0)
                self.total_move_score = data.get('total_move_score', 0)
                self.prev_win_rate = (self.win_count / self.total_games) * 100 if self.total_games > 0 else 0
            print("Agent data loaded successfully.")

            # Adjust weights based on historical win rate
            if self.prev_win_rate < 50:
                self.defensive_weight = 7
                self.offensive_weight = 5
            else:
                self.defensive_weight = 5
                self.offensive_weight = 10
        else:
            print("No saved agent data found. Starting fresh.")
            self.defensive_weight = 5  # Default weights
            self.offensive_weight = 5

    def write_performance_to_file(self):
        """Writes performance metrics for Player 1 to a file."""
        win_rate = (self.win_count / self.total_games) * 100 if self.total_games > 0 else 0
        improvement = win_rate - self.prev_win_rate
        avg_move_score = self.total_move_score / self.total_games if self.total_games > 0 else 0
        self.prev_win_rate = win_rate
        
        # Create or append to stats.txt file
        with open("stats.txt", "a") as file:
            file.write(f"\n===== Game {self.total_games} Summary =====\n")
            file.write(f"Turns Taken: {self.turns_in_game}\n")
            file.write(f"Win Rate: {win_rate:.2f}% (Improvement: {improvement:+.2f}%)\n")
            file.write(f"Offensive Moves: {self.offensive_moves}\n")
            file.write(f"Defensive Moves: {self.defensive_moves}\n")
            file.write(f"Average Move Score: {avg_move_score:.2f}\n")
            file.write("Top 5 Moves by Score:\n")
            top_moves = sorted(self.move_scores.items(), key=lambda x: -x[1])[:5]
            for move, score in top_moves:
                file.write(f"Move: {move}, Score: {score}\n")
            file.write("=================================\n")
