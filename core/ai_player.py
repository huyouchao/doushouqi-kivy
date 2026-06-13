import math
import random

from constants import BLUE_DEN, PIECE_RANK, RED_DEN


DIFFICULTY_PROFILES = {
    "1": {"label": "1级 入门", "depth": 0, "top_k": 8, "randomness": 0.70},
    "2": {"label": "2级 新手", "depth": 0, "top_k": 6, "randomness": 0.50},
    "3": {"label": "3级 简单", "depth": 0, "top_k": 5, "randomness": 0.30},
    "4": {"label": "4级 稳定", "depth": 1, "top_k": 6, "randomness": 0.18},
    "5": {"label": "5级 普通", "depth": 1, "top_k": 8, "randomness": 0.08},
    "6": {"label": "6级 进阶", "depth": 2, "top_k": 7, "randomness": 0.04},
    "7": {"label": "7级 强手", "depth": 2, "top_k": 9, "randomness": 0.0},
    "8": {"label": "8级 困难", "depth": 3, "top_k": 8, "randomness": 0.0},
    "9": {"label": "9级 大师", "depth": 3, "top_k": 10, "randomness": 0.0},
    "10": {"label": "10级 至尊", "depth": 4, "top_k": 7, "randomness": 0.0},
}


class AIPlayer:
    def __init__(self, color, difficulty="2"):
        self.color = color
        self.difficulty = difficulty if difficulty in DIFFICULTY_PROFILES else "2"

    def set_difficulty(self, difficulty):
        self.difficulty = difficulty if difficulty in DIFFICULTY_PROFILES else "2"

    def get_best_move(self, game_logic):
        moves = game_logic.get_all_valid_moves(self.color)
        if not moves:
            return None

        profile = DIFFICULTY_PROFILES[self.difficulty]
        ordered_moves = self._order_moves(game_logic, moves, self.color)
        if profile["depth"] <= 0:
            return self._pick_shallow_move(ordered_moves, profile)

        candidate_moves = ordered_moves[: profile["top_k"]]
        best_score = -math.inf
        best_moves = []
        for _, move in candidate_moves:
            score = self._score_move_by_search(game_logic, move, profile)
            if score > best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)
        return random.choice(best_moves) if best_moves else candidate_moves[0][1]

    def _pick_shallow_move(self, ordered_moves, profile):
        top_moves = ordered_moves[: profile["top_k"]]
        if not top_moves:
            return None
        if random.random() < profile["randomness"]:
            return random.choice(top_moves)[1]
        return top_moves[0][1]

    def _score_move_by_search(self, game_logic, move, profile):
        clone = game_logic.clone()
        if not clone.move_piece(*move[0], *move[1]):
            return -math.inf
        return self._minimax(
            clone,
            depth=profile["depth"],
            alpha=-math.inf,
            beta=math.inf,
            maximizing=False,
            top_k=profile["top_k"],
        )

    def _minimax(self, game_logic, depth, alpha, beta, maximizing, top_k):
        if depth == 0 or game_logic.is_game_over():
            return self._evaluate_board(game_logic)

        color = self.color if maximizing else self._opponent_color()
        moves = game_logic.get_all_valid_moves(color)
        if not moves:
            return self._evaluate_board(game_logic)

        ordered_moves = self._order_moves(game_logic, moves, color)[:top_k]

        if maximizing:
            best_value = -math.inf
            for _, move in ordered_moves:
                clone = game_logic.clone()
                if not clone.move_piece(*move[0], *move[1]):
                    continue
                best_value = max(
                    best_value,
                    self._minimax(clone, depth - 1, alpha, beta, False, top_k),
                )
                alpha = max(alpha, best_value)
                if beta <= alpha:
                    break
            return best_value

        best_value = math.inf
        for _, move in ordered_moves:
            clone = game_logic.clone()
            if not clone.move_piece(*move[0], *move[1]):
                continue
            best_value = min(
                best_value,
                self._minimax(clone, depth - 1, alpha, beta, True, top_k),
            )
            beta = min(beta, best_value)
            if beta <= alpha:
                break
        return best_value

    def _order_moves(self, game_logic, moves, color):
        scored = []
        for move in moves:
            score = self._evaluate_move_heuristic(game_logic, move, color)
            scored.append((score, move))
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored

    def _evaluate_move_heuristic(self, game_logic, move, color):
        (from_row, from_col), (to_row, to_col) = move
        piece = game_logic.get_piece(from_row, from_col)
        target = game_logic.get_piece(to_row, to_col)

        score = 0
        if not piece:
            return score

        if target and target.color != color:
            score += PIECE_RANK[target.animal] * 120
            score += 50

        if game_logic.can_jump_over_river(piece, from_row, from_col, to_row, to_col):
            score += 25

        if game_logic.is_river(to_row, to_col) and piece.rank == 1:
            score += 10

        if game_logic.is_trap(to_row, to_col, color):
            score -= 45

        enemy_den = BLUE_DEN if color == "red" else RED_DEN
        if (to_row, to_col) == enemy_den:
            score += 100000

        distance = abs(to_row - enemy_den[0]) + abs(to_col - enemy_den[1])
        score += max(0, 16 - distance) * 8
        score += PIECE_RANK[piece.animal] * 2
        return score

    def _evaluate_board(self, game_logic):
        if game_logic.is_game_over():
            if game_logic.winner == self.color:
                return 100000
            if game_logic.winner == self._opponent_color():
                return -100000
            return 0

        score = 0
        my_mobility = len(game_logic.get_all_valid_moves(self.color))
        enemy_color = self._opponent_color()
        enemy_mobility = len(game_logic.get_all_valid_moves(enemy_color))

        for row in range(7):
            for col in range(9):
                piece = game_logic.get_piece(row, col)
                if not piece:
                    continue

                direction = 1 if piece.color == self.color else -1
                value = PIECE_RANK[piece.animal] * 120
                enemy_den = BLUE_DEN if piece.color == "red" else RED_DEN
                distance = abs(row - enemy_den[0]) + abs(col - enemy_den[1])
                advancement = max(0, 16 - distance) * 6
                trap_penalty = 60 if game_logic.is_trap(row, col, piece.color) else 0
                river_bonus = 12 if game_logic.is_river(row, col) and piece.rank == 1 else 0
                score += direction * (value + advancement + river_bonus - trap_penalty)

        score += (my_mobility - enemy_mobility) * 4
        score -= game_logic.steps_without_capture * 0.3
        return score

    def _opponent_color(self):
        return "red" if self.color == "blue" else "blue"
