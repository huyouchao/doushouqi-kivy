import copy

from constants import *


RAT_RANK = 1
TIGER_RANK = 6
LION_RANK = 7
ELEPHANT_RANK = 8
NO_CAPTURE_DRAW_LIMIT = 100
REPETITION_DRAW_LIMIT = 3


class Piece:
    def __init__(self, animal, color, row, col):
        self.animal = animal
        self.color = color
        self.row = row
        self.col = col
        self.rank = PIECE_RANK[animal]

    def __eq__(self, other):
        if not other:
            return False
        return self.animal == other.animal and self.color == other.color

    def to_dict(self):
        return {
            "animal": self.animal,
            "color": self.color,
            "row": self.row,
            "col": self.col,
        }


class GameLogic:
    def __init__(self):
        self.board = [[None for _ in range(BOARD_COLS)] for _ in range(BOARD_ROWS)]
        self.current_turn = "red"
        self.winner = None
        self.game_over = False
        self.draw_reason = None
        self.move_history = []
        self.steps_without_capture = 0
        self.repetition_counts = {}
        self.last_move_info = None
        self.init_board()
        self._record_position()

    def init_board(self):
        for row, col, color, animal in INITIAL_BOARD:
            self.board[row][col] = Piece(animal, color, row, col)

    def reset(self):
        self.__init__()

    def get_piece(self, row, col):
        if 0 <= row < BOARD_ROWS and 0 <= col < BOARD_COLS:
            return self.board[row][col]
        return None

    def is_river(self, row, col):
        return (row, col) in RIVER_CELLS

    def is_trap(self, row, col, color):
        if color == "red":
            return (row, col) in BLUE_TRAPS
        return (row, col) in RED_TRAPS

    def is_own_den(self, row, col, color):
        if color == "red":
            return (row, col) == RED_DEN
        return (row, col) == BLUE_DEN

    def is_enemy_den(self, row, col, color):
        if color == "red":
            return (row, col) == BLUE_DEN
        return (row, col) == RED_DEN

    def can_eat(self, attacker, defender, defender_row, defender_col):
        if not defender:
            return True

        if self.is_trap(defender_row, defender_col, attacker.color):
            return True

        if attacker.rank == RAT_RANK and defender.rank == ELEPHANT_RANK:
            return True

        if attacker.rank == ELEPHANT_RANK and defender.rank == RAT_RANK:
            return False

        return attacker.rank >= defender.rank

    def can_jump_over_river(self, piece, from_row, from_col, to_row, to_col):
        if piece.rank not in (LION_RANK, TIGER_RANK):
            return False

        row_diff = abs(from_row - to_row)
        col_diff = abs(from_col - to_col)
        if row_diff + col_diff <= 1:
            return False

        if from_row != to_row and from_col != to_col:
            return False

        if from_row == to_row:
            step = 1 if to_col > from_col else -1
            crossed_river = False
            for col in range(from_col + step, to_col, step):
                if not self.is_river(from_row, col):
                    return False
                crossed_river = True
                piece_in_river = self.get_piece(from_row, col)
                if piece_in_river and piece_in_river.rank == RAT_RANK:
                    return False
            return crossed_river

        step = 1 if to_row > from_row else -1
        crossed_river = False
        for row in range(from_row + step, to_row, step):
            if not self.is_river(row, from_col):
                return False
            crossed_river = True
            piece_in_river = self.get_piece(row, from_col)
            if piece_in_river and piece_in_river.rank == RAT_RANK:
                return False
        return crossed_river

    def can_enter_river(self, piece, to_row, to_col):
        if not self.is_river(to_row, to_col):
            return True
        return piece.rank == RAT_RANK

    def _is_valid_move(self, from_row, from_col, to_row, to_col, ignore_turn=False):
        if self.game_over:
            return False

        piece = self.get_piece(from_row, from_col)
        if not piece:
            return False

        if not ignore_turn and piece.color != self.current_turn:
            return False

        if not (0 <= to_row < BOARD_ROWS and 0 <= to_col < BOARD_COLS):
            return False

        if from_row == to_row and from_col == to_col:
            return False

        if self.is_own_den(to_row, to_col, piece.color):
            return False

        row_diff = abs(from_row - to_row)
        col_diff = abs(from_col - to_col)
        if self.can_jump_over_river(piece, from_row, from_col, to_row, to_col):
            pass
        elif row_diff + col_diff != 1:
            return False

        if not self.can_enter_river(piece, to_row, to_col):
            return False

        target_piece = self.get_piece(to_row, to_col)
        if target_piece:
            if target_piece.color == piece.color:
                return False
            if not self.can_eat(piece, target_piece, to_row, to_col):
                return False

        return True

    def is_valid_move(self, from_row, from_col, to_row, to_col):
        return self._is_valid_move(from_row, from_col, to_row, to_col)

    def _begin_last_move_info(self, piece, from_row, from_col, to_row, to_col, target_piece):
        jumped_river = self.can_jump_over_river(piece, from_row, from_col, to_row, to_col)
        entered_river = not self.is_river(from_row, from_col) and self.is_river(to_row, to_col)
        return {
            "from": (from_row, from_col),
            "to": (to_row, to_col),
            "piece": piece.animal,
            "color": piece.color,
            "captured": target_piece.animal if target_piece else None,
            "captured_color": target_piece.color if target_piece else None,
            "jumped_river": jumped_river,
            "entered_river": entered_river,
            "entered_trap": self.is_trap(to_row, to_col, piece.color),
            "won": False,
            "draw": False,
            "draw_reason": None,
            "win_reason": None,
        }

    def move_piece(self, from_row, from_col, to_row, to_col):
        if not self.is_valid_move(from_row, from_col, to_row, to_col):
            return False

        piece = self.get_piece(from_row, from_col)
        target_piece = self.get_piece(to_row, to_col)
        opponent_color = "blue" if piece.color == "red" else "red"
        self.last_move_info = self._begin_last_move_info(piece, from_row, from_col, to_row, to_col, target_piece)

        self.move_history.append(copy.deepcopy(self.last_move_info))
        if target_piece:
            self.steps_without_capture = 0
        else:
            self.steps_without_capture += 1

        self.board[to_row][to_col] = piece
        self.board[from_row][from_col] = None
        piece.row = to_row
        piece.col = to_col

        if self.is_enemy_den(to_row, to_col, piece.color):
            self._set_winner(piece.color, "entered_den")
            return True

        if not self._has_pieces(opponent_color):
            self._set_winner(piece.color, "captured_all")
            return True

        if not self.has_any_move(opponent_color):
            self._set_winner(piece.color, "no_legal_moves")
            return True

        self.current_turn = opponent_color

        if self.steps_without_capture >= NO_CAPTURE_DRAW_LIMIT:
            self._set_draw("no_capture_limit")
            return True

        if self._record_position() >= REPETITION_DRAW_LIMIT:
            self._set_draw("threefold_repetition")
            return True

        return True

    def _set_winner(self, color, reason):
        self.winner = color
        self.game_over = True
        self.draw_reason = None
        if self.last_move_info:
            self.last_move_info["won"] = True
            self.last_move_info["win_reason"] = reason

    def _set_draw(self, reason):
        self.winner = None
        self.game_over = True
        self.draw_reason = reason
        if self.last_move_info:
            self.last_move_info["draw"] = True
            self.last_move_info["draw_reason"] = reason

    def _has_pieces(self, color):
        for row in range(BOARD_ROWS):
            for col in range(BOARD_COLS):
                piece = self.get_piece(row, col)
                if piece and piece.color == color:
                    return True
        return False

    def has_any_move(self, color):
        for row in range(BOARD_ROWS):
            for col in range(BOARD_COLS):
                piece = self.get_piece(row, col)
                if piece and piece.color == color:
                    for to_row in range(BOARD_ROWS):
                        for to_col in range(BOARD_COLS):
                            if self._is_valid_move(row, col, to_row, to_col, ignore_turn=True):
                                return True
        return False

    def get_valid_moves(self, row, col):
        """获取指定棋子的所有合法走法目标位置列表，返回 [(to_row, to_col), ...]"""
        moves = []
        for to_row in range(BOARD_ROWS):
            for to_col in range(BOARD_COLS):
                if self._is_valid_move(row, col, to_row, to_col, ignore_turn=True):
                    moves.append((to_row, to_col))
        return moves

    def get_all_valid_moves(self, color):
        moves = []
        for row in range(BOARD_ROWS):
            for col in range(BOARD_COLS):
                piece = self.get_piece(row, col)
                if piece and piece.color == color:
                    for to_row in range(BOARD_ROWS):
                        for to_col in range(BOARD_COLS):
                            if self._is_valid_move(row, col, to_row, to_col, ignore_turn=True):
                                moves.append(((row, col), (to_row, to_col)))
        return moves

    def check_winner(self):
        return self.winner

    def is_draw(self):
        return self.game_over and self.winner is None

    def is_game_over(self):
        return self.game_over

    def get_board_state(self):
        return copy.deepcopy(self.board)

    def get_last_move_info(self):
        return copy.deepcopy(self.last_move_info)

    def _board_signature(self):
        cells = []
        for row in range(BOARD_ROWS):
            for col in range(BOARD_COLS):
                piece = self.get_piece(row, col)
                if piece:
                    cells.append(f"{piece.color}:{piece.animal}:{row}:{col}")
        return f"{self.current_turn}|{'|'.join(cells)}"

    def _record_position(self):
        signature = self._board_signature()
        self.repetition_counts[signature] = self.repetition_counts.get(signature, 0) + 1
        return self.repetition_counts[signature]

    def to_dict(self):
        pieces = []
        for row in range(BOARD_ROWS):
            for col in range(BOARD_COLS):
                piece = self.get_piece(row, col)
                if piece:
                    pieces.append(piece.to_dict())
        return {
            "pieces": pieces,
            "current_turn": self.current_turn,
            "winner": self.winner,
            "game_over": self.game_over,
            "draw_reason": self.draw_reason,
            "move_history": copy.deepcopy(self.move_history),
            "steps_without_capture": self.steps_without_capture,
            "repetition_counts": copy.deepcopy(self.repetition_counts),
            "last_move_info": copy.deepcopy(self.last_move_info),
        }

    @classmethod
    def from_dict(cls, data):
        game = cls.__new__(cls)
        game.board = [[None for _ in range(BOARD_COLS)] for _ in range(BOARD_ROWS)]
        game.current_turn = data.get("current_turn", "red")
        game.winner = data.get("winner")
        game.game_over = data.get("game_over", bool(game.winner))
        game.draw_reason = data.get("draw_reason")
        game.move_history = copy.deepcopy(data.get("move_history", []))
        game.steps_without_capture = data.get("steps_without_capture", 0)
        game.repetition_counts = copy.deepcopy(data.get("repetition_counts", {}))
        game.last_move_info = copy.deepcopy(data.get("last_move_info"))

        for piece_data in data.get("pieces", []):
            piece = Piece(
                piece_data["animal"],
                piece_data["color"],
                piece_data["row"],
                piece_data["col"],
            )
            game.board[piece.row][piece.col] = piece

        if not game.repetition_counts:
            game.repetition_counts = {}
            game._record_position()
        return game

    def clone(self):
        return GameLogic.from_dict(self.to_dict())
