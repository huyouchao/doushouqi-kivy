"""
阶段4验证：走棋交互（双人对战）
点击己方棋子选中，点击目标格走棋
红蓝方轮流操作
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui'))

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.properties import ListProperty, ObjectProperty, StringProperty

from constants import BOARD_ROWS, BOARD_COLS, CELL_SIZE, INITIAL_BOARD, COLORS
from game_logic import GameLogic
from board_widget import BoardWidget, hex_to_rgb


class GameScreen(BoxLayout):
    """游戏主界面：棋盘 + 信息栏"""

    # 当前回合文字
    turn_text = StringProperty('红方回合')
    # 游戏状态文字
    status_text = StringProperty('请点击红方棋子')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'

        # 创建游戏逻辑
        self.game_logic = GameLogic()

        # 上方信息栏
        info_bar = BoxLayout(orientation='horizontal', size_hint_y=0.08, spacing=10, padding=5)
        self.turn_label = Label(
            text='红方回合',
            font_size='18sp',
            color=hex_to_rgb(COLORS['red_piece']),
            size_hint_x=0.5,
        )
        self.status_label = Label(
            text='请点击红方棋子',
            font_size='16sp',
            color=hex_to_rgb(COLORS['board_line']),
            size_hint_x=0.5,
        )
        info_bar.add_widget(self.turn_label)
        info_bar.add_widget(self.status_label)

        # 棋盘区域
        self.board = BoardWidget(size_hint_y=0.92)
        self.board.cell_size = CELL_SIZE
        self.board.board_margin = 20

        # 同步棋子数据到棋盘
        self._sync_pieces()

        # 注册棋盘点击回调
        self.board.on_cell_click = self._on_cell_click

        self.add_widget(info_bar)
        self.add_widget(self.board)

    def _sync_pieces(self):
        """从 GameLogic 同步棋子数据到棋盘"""
        pieces = []
        for row in range(BOARD_ROWS):
            for col in range(BOARD_COLS):
                piece = self.game_logic.get_piece(row, col)
                if piece:
                    pieces.append((piece.row, piece.col, piece.color, piece.animal))
        self.board.pieces_data = pieces

    def _update_turn_display(self):
        """更新回合显示"""
        turn = self.game_logic.current_turn
        if turn == 'red':
            self.turn_label.text = '红方回合'
            self.turn_label.color = hex_to_rgb(COLORS['red_piece'])
            self.status_label.text = '请点击红方棋子'
        else:
            self.turn_label.text = '蓝方回合'
            self.turn_label.color = hex_to_rgb(COLORS['blue_piece'])
            self.status_label.text = '请点击蓝方棋子'

        # 检查游戏是否结束
        if self.game_logic.game_over:
            winner = self.game_logic.winner
            if winner:
                self.status_label.text = f'{winner}方获胜！'
                self.turn_label.text = '游戏结束'
            elif self.game_logic.draw_reason:
                self.status_label.text = f'和棋：{self.game_logic.draw_reason}'
                self.turn_label.text = '游戏结束'

    def _on_cell_click(self, row, col):
        """处理棋盘格子点击事件"""
        gl = self.game_logic

        # 游戏已结束，不再响应
        if gl.game_over:
            self.status_label.text = '游戏已结束'
            return

        current_turn = gl.current_turn
        clicked_piece = gl.get_piece(row, col)

        # 当前有选中棋子
        if self.board.selected_pos:
            sel_row, sel_col = self.board.selected_pos

            # 点击的是同一个棋子 → 取消选中
            if row == sel_row and col == sel_col:
                self.board.selected_pos = []
                self.board.valid_moves = []
                self._update_turn_display()
                return

            # 点击的是自己方另一个棋子 → 切换选中
            if clicked_piece and clicked_piece.color == current_turn:
                self._select_piece(row, col)
                return

            # 点击目标格 → 尝试走棋
            result = gl.move_piece(sel_row, sel_col, row, col)
            if result:
                # 走棋成功
                self.board.selected_pos = []
                self.board.valid_moves = []
                self._sync_pieces()
                self._update_turn_display()

                # 检查吃子信息
                if gl.last_move_info and gl.last_move_info.get('captured'):
                    captured = gl.last_move_info['captured']
                    self.status_label.text = f'{current_turn}方{gl.last_move_info["animal"]}吃了{captured["color"]}方{captured["animal"]}！'
                elif gl.game_over:
                    if gl.winner:
                        self.status_label.text = f'{gl.winner}方获胜！'
                    elif gl.draw_reason:
                        self.status_label.text = f'和棋：{gl.draw_reason}'
                return
            else:
                # 走棋无效
                self.status_label.text = '走棋无效，请重新选择'
                self.board.selected_pos = []
                self.board.valid_moves = []
                return

        # 没有选中棋子，尝试选中
        if clicked_piece and clicked_piece.color == current_turn:
            self._select_piece(row, col)
        else:
            if clicked_piece:
                self.status_label.text = f'当前是{current_turn}方回合，不能选择{clicked_piece.color}方棋子'
            else:
                self.status_label.text = f'请选择{current_turn}方的棋子'

    def _select_piece(self, row, col):
        """选中一个棋子，显示可走位置"""
        gl = self.game_logic
        piece = gl.get_piece(row, col)
        if not piece:
            return

        self.board.selected_pos = [row, col]

        # 获取所有合法走法
        valid_moves = gl.get_valid_moves(row, col)
        move_positions = [(to_row, to_col) for (from_row, from_col, to_row, to_col) in valid_moves]
        self.board.valid_moves = move_positions

        self.status_label.text = f'选中 {piece.color}方{piece.animal}，请点击目标格'


class BoardTestApp(App):
    """走棋交互验证 App"""

    def build(self):
        Window.clearcolor = hex_to_rgb(COLORS['background'])

        # 窗口大小适配棋盘
        board_width = BOARD_COLS * CELL_SIZE + 40
        board_height = BOARD_ROWS * CELL_SIZE + 120
        Window.size = (board_width, board_height + 40)

        return GameScreen()


if __name__ == '__main__':
    BoardTestApp().run()