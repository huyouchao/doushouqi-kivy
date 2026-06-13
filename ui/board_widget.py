"""
board_widget.py - Kivy 棋盘绘制 Widget
支持：Y轴翻转、中文字体、走棋动画、起始位置影子
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'core'))

from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Line, Ellipse
from kivy.core.text import Label as CoreLabel
from kivy.properties import NumericProperty, ListProperty
from kivy.clock import Clock

from constants import (
    BOARD_ROWS, BOARD_COLS, PIECE_RANK,
    RIVER_CELLS, BLUE_DEN, RED_DEN,
    BLUE_TRAPS, RED_TRAPS, COLORS, ANIMALS,
)
from platform_services.resources import get_chinese_font


CHINESE_FONT = get_chinese_font()


def hex_to_rgb(hex_color):
    """将颜色转换为 Kivy RGBA (0-1 范围)，支持十六进制和名称"""
    named_colors = {
        'white': (1.0, 1.0, 1.0, 1.0),
        'black': (0.0, 0.0, 0.0, 1.0),
        'red': (1.0, 0.0, 0.0, 1.0),
        'green': (0.0, 1.0, 0.0, 1.0),
        'blue': (0.0, 0.0, 1.0, 1.0),
    }
    if hex_color in named_colors:
        return named_colors[hex_color]

    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return (r, g, b, 1.0)


# 预转换所有颜色
KV_COLORS = {k: hex_to_rgb(v) for k, v in COLORS.items()}


class BoardWidget(Widget):
    """斗兽棋棋盘绘制组件（支持走棋动画 + 起始位置影子）"""

    # 棋盘参数
    cell_size = NumericProperty(70)
    board_margin = NumericProperty(20)  # 棋盘四周留白

    # 棋子数据（由外部设置）
    pieces_data = ListProperty([])

    # 选中棋子位置
    selected_pos = ListProperty([])

    # 可走位置列表
    valid_moves = ListProperty([])

    # 上一步起始位置（影子标记）
    last_move_from = ListProperty([])

    # 上一步终点位置（影子标记）
    last_move_to = ListProperty([])

    # 点击回调函数（由外部设置）
    on_cell_click = None

    # 走棋动画完成后的回调
    on_move_anim_done = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(
            pos=self._redraw,
            size=self._redraw,
            pieces_data=self._redraw,
            selected_pos=self._redraw,
            valid_moves=self._redraw,
            last_move_from=self._redraw,
            last_move_to=self._redraw,
        )

        # 动画状态
        self._animating = False
        self._anim_piece_info = None  # (color_name, animal)
        self._anim_from_cx = 0
        self._anim_from_cy = 0
        self._anim_to_cx = 0
        self._anim_to_cy = 0
        self._anim_progress = 0.0     # 0.0 ~ 1.0
        self._anim_duration = 0.3     # 动画时长（秒）
        self._anim_pieces_data = None # 动画期间的棋子数据（不含正在动画的棋子）

    def start_move_animation(self, from_row, from_col, to_row, to_col,
                              piece_color, piece_animal, new_pieces_data,
                              on_done=None):
        """启动走棋动画
        from_row/from_col: 起始位置
        to_row/to_col: 目标位置
        piece_color/piece_animal: 移动的棋子信息
        new_pieces_data: 动画结束后要设置的棋子数据
        on_done: 动画完成后的回调
        """
        self._animating = True
        self._anim_piece_info = (piece_color, piece_animal)
        self._anim_from_cx, self._anim_from_cy = self._cell_center(from_row, from_col)
        self._anim_to_cx, self._anim_to_cy = self._cell_center(to_row, to_col)
        self._anim_progress = 0.0
        self._anim_pieces_data = new_pieces_data
        self._anim_on_done = on_done

        # 设置起始位置影子
        self.last_move_from = [from_row, from_col]
        self.last_move_to = [to_row, to_col]

        # 启动动画定时器（约60fps）
        Clock.schedule_interval(self._anim_tick, 1.0 / 60.0)

    def _anim_tick(self, dt):
        """动画每帧更新"""
        if not self._animating:
            return False  # 停止定时器

        self._anim_progress += dt / self._anim_duration

        if self._anim_progress >= 1.0:
            self._anim_progress = 1.0
            self._animating = False

            # 动画结束，更新棋子数据
            if self._anim_pieces_data is not None:
                self.pieces_data = self._anim_pieces_data
                self._anim_pieces_data = None

            # 调用完成回调
            if self._anim_on_done:
                self._anim_on_done()
                self._anim_on_done = None

            return False  # 停止定时器

        # 重绘（动画中）
        self._redraw()
        return True  # 继续定时器

    def is_animating(self):
        """是否正在播放动画"""
        return self._animating

    def on_touch_down(self, touch):
        """处理鼠标/触摸点击事件"""
        if not self.collide_point(touch.x, touch.y):
            return False

        # 动画期间不接受点击
        if self._animating:
            return True

        # 将像素坐标转换为棋盘行列
        row, col = self._pixel_to_cell(touch.x, touch.y)
        if row is not None and self.on_cell_click:
            self.on_cell_click(row, col)
        return True

    def _pixel_to_cell(self, px, py):
        """将像素坐标转换为棋盘行列，如果不在棋盘范围内返回 (None, None)"""
        cs = self.cell_size
        board_x, board_y = self._board_origin()

        col = int((px - board_x) / cs)
        row = BOARD_ROWS - 1 - int((py - board_y) / cs)

        if 0 <= row < BOARD_ROWS and 0 <= col < BOARD_COLS:
            return (row, col)
        return (None, None)

    def _redraw(self, *args):
        """全量重绘棋盘"""
        self.canvas.clear()
        self._draw_background()
        self._draw_board_cells()
        self._draw_special_cells()
        self._draw_grid_lines()
        self._draw_last_move_shadow()
        self._draw_pieces()
        self._draw_animating_piece()
        self._draw_selection()
        self._draw_valid_moves()

    def _cell_pos(self, row, col):
        """将棋盘行列转换为画布像素坐标（左上角）
        Kivy的y=0在底部，所以需要翻转：
        row=0 在最上面，row=BOARD_ROWS-1 在最下面
        """
        board_x, board_y = self._board_origin()
        x = board_x + col * self.cell_size
        y = board_y + (BOARD_ROWS - row - 1) * self.cell_size
        return (x, y)

    def _cell_center(self, row, col):
        """将棋盘行列转换为画布像素坐标（中心点）"""
        x, y = self._cell_pos(row, col)
        return (x + self.cell_size / 2, y + self.cell_size / 2)

    def _board_origin(self):
        """计算棋盘在当前容器中的左下角坐标，使其始终居中显示。"""
        board_w = BOARD_COLS * self.cell_size
        board_h = BOARD_ROWS * self.cell_size
        x = self.x + max(self.board_margin, (self.width - board_w) / 2)
        y = self.y + max(self.board_margin, (self.height - board_h) / 2)
        return (x, y)

    def _draw_background(self):
        """绘制深绿色背景"""
        with self.canvas:
            Color(*KV_COLORS['background'])
            Rectangle(pos=self.pos, size=self.size)

    def _draw_board_cells(self):
        """绘制棋盘格子（深绿交替，河流蓝色）"""
        cs = self.cell_size
        river_set = set(RIVER_CELLS)
        trap_blue_set = set(BLUE_TRAPS)
        trap_red_set = set(RED_TRAPS)

        for row in range(BOARD_ROWS):
            for col in range(BOARD_COLS):
                x, y = self._cell_pos(row, col)
                pos_cell = (row, col)

                if pos_cell in river_set:
                    with self.canvas:
                        Color(*KV_COLORS['river'])
                        Rectangle(pos=(x, y), size=(cs, cs))
                elif pos_cell in trap_blue_set:
                    with self.canvas:
                        Color(*KV_COLORS['trap_blue'])
                        Rectangle(pos=(x, y), size=(cs, cs))
                elif pos_cell in trap_red_set:
                    with self.canvas:
                        Color(*KV_COLORS['trap_red'])
                        Rectangle(pos=(x, y), size=(cs, cs))
                elif pos_cell == BLUE_DEN:
                    with self.canvas:
                        Color(*KV_COLORS['den_blue'])
                        Rectangle(pos=(x, y), size=(cs, cs))
                elif pos_cell == RED_DEN:
                    with self.canvas:
                        Color(*KV_COLORS['den_red'])
                        Rectangle(pos=(x, y), size=(cs, cs))
                else:
                    if (row + col) % 2 == 0:
                        with self.canvas:
                            Color(*KV_COLORS['cell_light'])
                            Rectangle(pos=(x, y), size=(cs, cs))
                    else:
                        with self.canvas:
                            Color(*KV_COLORS['cell_dark'])
                            Rectangle(pos=(x, y), size=(cs, cs))

    def _draw_special_cells(self):
        """在特殊格子上画文字标记（河流标'水', 陷阱标'陷', 兽穴标'穴'）"""
        cs = self.cell_size

        # 河流标记
        for (row, col) in RIVER_CELLS:
            cx, cy = self._cell_center(row, col)
            self._draw_centered_text('水', cx, cy, font_size=int(cs * 0.35),
                                     color=KV_COLORS['river_light'])

        # 陷阱标记
        for (row, col) in BLUE_TRAPS:
            cx, cy = self._cell_center(row, col)
            self._draw_centered_text('陷', cx, cy, font_size=int(cs * 0.35),
                                     color=(1, 1, 1, 0.7))
        for (row, col) in RED_TRAPS:
            cx, cy = self._cell_center(row, col)
            self._draw_centered_text('陷', cx, cy, font_size=int(cs * 0.35),
                                     color=(1, 1, 1, 0.7))

        # 兽穴标记
        cx, cy = self._cell_center(*BLUE_DEN)
        self._draw_centered_text('穴', cx, cy, font_size=int(cs * 0.45),
                                 color=(1, 1, 1, 0.8))
        cx, cy = self._cell_center(*RED_DEN)
        self._draw_centered_text('穴', cx, cy, font_size=int(cs * 0.45),
                                 color=(1, 1, 1, 0.8))

    def _draw_grid_lines(self):
        """绘制网格线"""
        cs = self.cell_size
        board_x, board_y = self._board_origin()
        top_y = board_y + BOARD_ROWS * cs
        bottom_y = board_y

        with self.canvas:
            Color(*KV_COLORS['board_line'])
            # 横线
            for row in range(BOARD_ROWS + 1):
                y = top_y - row * cs
                Line(points=[board_x, y, board_x + BOARD_COLS * cs, y], width=1.5)
            # 竖线
            for col in range(BOARD_COLS + 1):
                x = board_x + col * cs
                Line(points=[x, top_y, x, bottom_y], width=1.5)

    def _draw_last_move_shadow(self):
        """绘制上一步起始位置的影子标记（半透明边框 + 起点棋子虚影）"""
        if not self.last_move_from:
            return
        cs = self.cell_size

        # 起始位置：画一个醒目的半透明金色边框
        from_row, from_col = self.last_move_from
        x, y = self._cell_pos(from_row, from_col)
        with self.canvas:
            Color(1.0, 0.84, 0.0, 0.5)  # 半透明金色
            Line(rectangle=(x + 1, y + 1, cs - 2, cs - 2), width=2.5)

        # 起始位置：画半透明棋子虚影
        cx, cy = self._cell_center(from_row, from_col)
        piece_radius = cs * 0.40

        # 找到上一步移动的棋子颜色
        if self.last_move_to:
            to_row, to_col = self.last_move_to
            # 从当前棋子数据中找目标位置的棋子（那就是移动后的棋子）
            for piece_info in self.pieces_data:
                r, c, color_name, animal = piece_info
                if r == to_row and c == to_col:
                    # 画虚影
                    with self.canvas:
                        if color_name == 'red':
                            Color(0.91, 0.30, 0.24, 0.25)  # 半透明红
                        else:
                            Color(0.20, 0.60, 0.86, 0.25)  # 半透明蓝
                        Ellipse(pos=(cx - piece_radius, cy - piece_radius),
                                size=(piece_radius * 2, piece_radius * 2))
                    # 虚影上的半透明文字
                    self._draw_centered_text(animal, cx, cy,
                                             font_size=int(cs * 0.40),
                                             color=(1, 1, 1, 0.3))
                    break

        # 终点位置：画一个绿色边框标记
        if self.last_move_to:
            to_row, to_col = self.last_move_to
            x2, y2 = self._cell_pos(to_row, to_col)
            with self.canvas:
                Color(0.18, 0.80, 0.44, 0.6)  # 半透明绿色
                Line(rectangle=(x2 + 1, y2 + 1, cs - 2, cs - 2), width=2.5)

    def _draw_pieces(self):
        """绘制棋子（圆形 + 动物名文字），动画中的棋子除外"""
        cs = self.cell_size
        piece_radius = cs * 0.40

        # 如果正在动画，找出动画中的棋子位置（终点），跳过它
        anim_skip_pos = None
        if self._animating and self.last_move_to:
            anim_skip_pos = tuple(self.last_move_to)

        for piece_info in self.pieces_data:
            row, col, color_name, animal = piece_info

            # 跳过正在动画的棋子（它在终点位置，但动画还没结束）
            if anim_skip_pos and (row, col) == anim_skip_pos:
                continue

            cx, cy = self._cell_center(row, col)

            if color_name == 'red':
                piece_color = KV_COLORS['red_piece']
            else:
                piece_color = KV_COLORS['blue_piece']

            # 绘制棋子圆形
            with self.canvas:
                Color(*piece_color)
                Ellipse(pos=(cx - piece_radius, cy - piece_radius),
                        size=(piece_radius * 2, piece_radius * 2))

            # 绘制棋子边框（金色）
            with self.canvas:
                Color(1.0, 0.84, 0.0, 0.8)
                Line(circle=(cx, cy, piece_radius), width=1.5)

            # 绘制棋子文字（动物名）
            self._draw_centered_text(animal, cx, cy,
                                     font_size=int(cs * 0.40),
                                     color=KV_COLORS['piece_text'])

    def _draw_animating_piece(self):
        """绘制正在动画中的棋子（从起点滑动到终点）"""
        if not self._animating:
            return

        cs = self.cell_size
        piece_radius = cs * 0.40
        color_name, animal = self._anim_piece_info

        # 线性插值计算当前位置
        t = self._anim_progress
        cx = self._anim_from_cx + (self._anim_to_cx - self._anim_from_cx) * t
        cy = self._anim_from_cy + (self._anim_to_cy - self._anim_from_cy) * t

        if color_name == 'red':
            piece_color = KV_COLORS['red_piece']
        else:
            piece_color = KV_COLORS['blue_piece']

        # 绘制棋子圆形
        with self.canvas:
            Color(*piece_color)
            Ellipse(pos=(cx - piece_radius, cy - piece_radius),
                    size=(piece_radius * 2, piece_radius * 2))

        # 绘制棋子边框（金色）
        with self.canvas:
            Color(1.0, 0.84, 0.0, 0.8)
            Line(circle=(cx, cy, piece_radius), width=1.5)

        # 绘制棋子文字
        self._draw_centered_text(animal, cx, cy,
                                 font_size=int(cs * 0.40),
                                 color=KV_COLORS['piece_text'])

    def _draw_selection(self):
        """绘制选中棋子的高亮框"""
        if not self.selected_pos:
            return
        cs = self.cell_size
        row, col = self.selected_pos
        x, y = self._cell_pos(row, col)

        with self.canvas:
            Color(*KV_COLORS['selected'])
            Line(rectangle=(x + 2, y + 2, cs - 4, cs - 4), width=3)

    def _draw_valid_moves(self):
        """绘制可走位置的提示标记"""
        if not self.valid_moves:
            return
        cs = self.cell_size
        mark_radius = cs * 0.12

        for (row, col) in self.valid_moves:
            cx, cy = self._cell_center(row, col)

            with self.canvas:
                Color(*KV_COLORS['valid_move'])
                Ellipse(pos=(cx - mark_radius, cy - mark_radius),
                        size=(mark_radius * 2, mark_radius * 2))

    def _draw_centered_text(self, text, cx, cy, font_size=24, color=(1, 1, 1, 1)):
        """在指定位置绘制居中文字（使用中文字体）"""
        kwargs = {'text': text, 'font_size': font_size}
        if CHINESE_FONT:
            kwargs['font_name'] = CHINESE_FONT

        label = CoreLabel(**kwargs)
        label.refresh()
        texture = label.texture
        if texture is None:
            return

        tw, th = texture.size
        with self.canvas:
            Color(*color)
            Rectangle(
                pos=(cx - tw / 2, cy - th / 2),
                size=(tw, th),
                texture=texture,
            )
