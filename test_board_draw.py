"""
阶段3验证：棋盘静态绘制
运行此文件，应看到完整棋盘 + 16个棋子的初始布局
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui'))

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from kivy.properties import ListProperty

from constants import BOARD_ROWS, BOARD_COLS, CELL_SIZE, INITIAL_BOARD, COLORS
from board_widget import BoardWidget, hex_to_rgb


class BoardTestApp(App):
    """棋盘绘制验证 App"""

    def build(self):
        # 窗口背景深绿
        Window.clearcolor = hex_to_rgb(COLORS['background'])

        # 窗口大小适配棋盘
        board_width = BOARD_COLS * CELL_SIZE + 40
        board_height = BOARD_ROWS * CELL_SIZE + 40
        Window.size = (board_width, board_height)

        # 创建棋盘组件
        board = BoardWidget()
        board.cell_size = CELL_SIZE
        board.board_margin = 20

        # 设置初始棋子数据
        board.pieces_data = list(INITIAL_BOARD)

        # 标题信息
        from kivy.uix.label import Label

        layout = BoxLayout(orientation='vertical', spacing=5)

        info = Label(
            text='斗兽棋 Kivy 版 - 阶段3验证：棋盘静态绘制',
            font_size='16sp',
            color=hex_to_rgb(COLORS['board_line']),
            size_hint_y=0.06,
        )

        # 棋盘占据主要空间
        board.size_hint_y = 0.94

        layout.add_widget(info)
        layout.add_widget(board)

        return layout


if __name__ == '__main__':
    BoardTestApp().run()