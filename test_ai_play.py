"""
阶段5+6验证：AI 对战 + 音效系统
红方由玩家操作，蓝方由 AI 自动走棋
支持：走棋动画 + 起始位置影子 + 中文字体 + Y轴方向 + 音效
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui'))

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.properties import ListProperty, ObjectProperty, StringProperty

from constants import BOARD_ROWS, BOARD_COLS, CELL_SIZE, INITIAL_BOARD, COLORS, RIVER_CELLS
from game_logic import GameLogic
from ai_player import AIPlayer, DIFFICULTY_PROFILES
from sound_manager import SoundManager
from board_widget import BoardWidget, hex_to_rgb, CHINESE_FONT


def _mk_label(text, font_size='18sp', color=(1,1,1,1), **kwargs):
    """创建带中文字体的 Label"""
    lbl = Label(text=text, font_size=font_size, color=color, **kwargs)
    if CHINESE_FONT:
        lbl.font_name = CHINESE_FONT
    return lbl


def _mk_button(text, font_size='14sp', **kwargs):
    """创建带中文字体的 Button"""
    btn = Button(text=text, font_size=font_size, **kwargs)
    if CHINESE_FONT:
        btn.font_name = CHINESE_FONT
    return btn


def _mk_spinner(text, values, font_size='14sp', **kwargs):
    """创建带中文字体的 Spinner（包括下拉列表项）"""
    class ChineseSpinnerOption(SpinnerOption):
        def __init__(self, **kw):
            super().__init__(**kw)
            if CHINESE_FONT:
                self.font_name = CHINESE_FONT

    sp = Spinner(text=text, values=values, font_size=font_size,
                 option_cls=ChineseSpinnerOption, **kwargs)
    if CHINESE_FONT:
        sp.font_name = CHINESE_FONT
    return sp


class GameScreen(BoxLayout):
    """游戏主界面：信息栏 + 棋盘 + AI控制 + 音效"""

    turn_text = StringProperty('红方回合')
    status_text = StringProperty('请点击红方棋子')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'

        # 创建游戏逻辑
        self.game_logic = GameLogic()

        # AI 玩家（蓝方）
        self.ai_player = AIPlayer(color='blue', difficulty='5')
        self.ai_pending = False  # AI 是否正在思考

        # 音效管理器
        self.sound_manager = SoundManager()

        # 上方信息栏 + 难度选择
        info_bar = BoxLayout(orientation='horizontal', size_hint_y=0.08, spacing=5, padding=5)
        self.turn_label = _mk_label(
            '红方回合（你）',
            font_size='18sp',
            color=hex_to_rgb(COLORS['red_piece']),
            size_hint_x=0.35,
        )
        self.status_label = _mk_label(
            '请点击红方棋子',
            font_size='16sp',
            color=hex_to_rgb(COLORS['board_line']),
            size_hint_x=0.35,
        )

        # 难度选择下拉
        difficulty_labels = [DIFFICULTY_PROFILES[k]['label'] for k in DIFFICULTY_PROFILES]
        self.difficulty_spinner = _mk_spinner(
            '5级 普通',
            difficulty_labels,
            font_size='14sp',
            size_hint_x=0.30,
            background_color=hex_to_rgb(COLORS['den_blue']),
            color=(1, 1, 1, 1),
        )
        self.difficulty_spinner.bind(text=self._on_difficulty_change)

        info_bar.add_widget(self.turn_label)
        info_bar.add_widget(self.status_label)
        info_bar.add_widget(self.difficulty_spinner)

        # 棋盘区域
        self.board = BoardWidget(size_hint_y=0.84)
        self.board.cell_size = CELL_SIZE
        self.board.board_margin = 20
        self.board.on_cell_click = self._on_cell_click

        # 底部按钮栏
        btn_bar = BoxLayout(orientation='horizontal', size_hint_y=0.08, spacing=5, padding=5)
        new_game_btn = _mk_button('新游戏', font_size='14sp',
                              background_color=hex_to_rgb(COLORS['den_blue']),
                              color=(1, 1, 1, 1))
        new_game_btn.bind(on_press=self._on_new_game)
        btn_bar.add_widget(new_game_btn)

        # 音效开关按钮
        self.sound_btn = _mk_button('音效:开', font_size='14sp',
                                    background_color=(0.2, 0.6, 0.2, 1),
                                    color=(1, 1, 1, 1))
        self.sound_btn.bind(on_press=self._on_toggle_sound)
        btn_bar.add_widget(self.sound_btn)

        self.add_widget(info_bar)
        self.add_widget(self.board)
        self.add_widget(btn_bar)

        # 同步棋子数据到棋盘
        self._sync_pieces()

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
        gl = self.game_logic
        if gl.game_over:
            if gl.winner:
                winner_name = '红方（你）' if gl.winner == 'red' else '蓝方（AI）'
                self.status_label.text = f'{winner_name}获胜！'
                self.turn_label.text = '游戏结束'
            elif gl.draw_reason:
                self.status_label.text = f'和棋：{gl.draw_reason}'
                self.turn_label.text = '游戏结束'
            return

        if gl.current_turn == 'red':
            self.turn_label.text = '红方回合（你）'
            self.turn_label.color = hex_to_rgb(COLORS['red_piece'])
            self.status_label.text = '请点击红方棋子'
        else:
            self.turn_label.text = '蓝方回合（AI）'
            self.turn_label.color = hex_to_rgb(COLORS['blue_piece'])
            self.status_label.text = 'AI 思考中...'

    def _on_difficulty_change(self, spinner, text):
        """难度选择变更"""
        for k, v in DIFFICULTY_PROFILES.items():
            if v['label'] == text:
                self.ai_player.set_difficulty(k)
                self.status_label.text = f'难度已设为：{text}'
                break

    def _on_new_game(self, button):
        """开始新游戏"""
        self.game_logic = GameLogic()
        self.board.selected_pos = []
        self.board.valid_moves = []
        self.board.last_move_from = []
        self.board.last_move_to = []
        self.ai_pending = False
        self._sync_pieces()
        self._update_turn_display()

    def _on_toggle_sound(self, button):
        """切换音效开关"""
        self.sound_manager.enabled = not self.sound_manager.enabled
        if self.sound_manager.enabled:
            self.sound_btn.text = '音效:开'
            self.sound_btn.background_color = (0.2, 0.6, 0.2, 1)
            self.sound_manager.play('move')  # 播放提示音
        else:
            self.sound_btn.text = '音效:关'
            self.sound_btn.background_color = (0.5, 0.2, 0.2, 1)

    def _get_move_sound(self, from_row, from_col, to_row, to_col, captured):
        """根据走棋类型判断该播放什么音效"""
        gl = self.game_logic

        # 吃子 → 吃子音
        if captured:
            return 'capture'

        # 跳河（狮虎跳过河流）→ 跳河音
        from_in_river = (from_row, from_col) in RIVER_CELLS
        to_in_river = (to_row, to_col) in RIVER_CELLS
        # 跳河：起点和终点都不在河里，但中间跨过了河
        if not from_in_river and not to_in_river:
            # 检查路径是否经过河流（同行或同列的跳跃）
            if from_row == to_row:
                # 横向跳河
                min_col = min(from_col, to_col)
                max_col = max(from_col, to_col)
                if any((from_row, c) in RIVER_CELLS for c in range(min_col + 1, max_col)):
                    return 'jump'
            elif from_col == to_col:
                # 纵向跳河
                min_row = min(from_row, to_row)
                max_row = max(from_row, to_row)
                if any((r, from_col) in RIVER_CELLS for r in range(min_row + 1, max_row)):
                    return 'jump'

        # 进入河流（鼠下水）→ 水音
        if to_in_river and not from_in_river:
            return 'rat_water'

        # 离开河流（鼠上岸）→ 水音
        if from_in_river and not to_in_river:
            return 'rat_water'

        # 进入对方陷阱 → 陷阱音
        moving_piece = gl.get_piece(to_row, to_col)
        if moving_piece:
            if moving_piece.color == 'red' and (to_row, to_col) in [(0, 2), (0, 4), (1, 3)]:
                return 'trap'
            if moving_piece.color == 'blue' and (to_row, to_col) in [(7, 3), (8, 2), (8, 4)]:
                return 'trap'

        # 普通走棋 → 走棋音
        return 'move'

    def _execute_move(self, from_row, from_col, to_row, to_col, is_ai=False):
        """执行走棋并播放动画和音效
        is_ai: 是否是AI走棋
        """
        gl = self.game_logic

        # 记住移动前的棋子信息（用于动画）
        piece = gl.get_piece(from_row, from_col)
        if not piece:
            return
        piece_color = piece.color
        piece_animal = piece.animal

        # 执行走棋
        result = gl.move_piece(from_row, from_col, to_row, to_col)
        if not result:
            return

        # 播放音效
        captured = gl.last_move_info and gl.last_move_info.get('captured')
        sound_name = self._get_move_sound(from_row, from_col, to_row, to_col, captured)
        self.sound_manager.play(sound_name)

        # 生成走棋后的棋子数据
        new_pieces = []
        for row in range(BOARD_ROWS):
            for col in range(BOARD_COLS):
                p = gl.get_piece(row, col)
                if p:
                    new_pieces.append((p.row, p.col, p.color, p.animal))

        # 清除选中状态
        self.board.selected_pos = []
        self.board.valid_moves = []

        # 吃子反馈文字（动画结束后显示）
        capture_msg = None
        if captured:
            cap = gl.last_move_info['captured']
            who = 'AI' if is_ai else '你'
            target = '你' if is_ai else 'AI'
            capture_msg = f'{who}的{gl.last_move_info["piece"]}吃了{target}的{cap}！'

        # 启动走棋动画
        self.board.start_move_animation(
            from_row, from_col, to_row, to_col,
            piece_color, piece_animal, new_pieces,
            on_done=lambda: self._on_move_anim_done(capture_msg, is_ai)
        )

    def _on_move_anim_done(self, capture_msg, is_ai):
        """走棋动画完成后的回调"""
        self._update_turn_display()

        # 显示吃子消息
        if capture_msg:
            self.status_label.text = capture_msg

        # 检查游戏结束，播放胜/负/和音效
        gl = self.game_logic
        if gl.game_over:
            self.ai_pending = False
            if gl.winner == 'red':
                self.sound_manager.play('win')
            elif gl.winner == 'blue':
                self.sound_manager.play('lose')
            elif gl.draw_reason:
                self.sound_manager.play('draw')
            return

        if gl.current_turn == 'blue' and not is_ai:
            # 玩家走完后，触发 AI
            self._trigger_ai_move()
        elif gl.current_turn == 'red' and is_ai:
            # AI走完后，等待玩家操作
            self.status_label.text = '请点击红方棋子'
            self.ai_pending = False

    def _on_cell_click(self, row, col):
        """处理棋盘格子点击事件"""
        gl = self.game_logic

        # 游戏已结束
        if gl.game_over:
            self.status_label.text = '游戏已结束，点击新游戏重新开始'
            return

        # 动画播放中不接受操作
        if self.board.is_animating():
            return

        # AI 回合时不接受玩家操作
        if gl.current_turn == 'blue':
            self.status_label.text = 'AI 思考中，请稍候...'
            return

        # AI 正在思考时不接受操作
        if self.ai_pending:
            return

        clicked_piece = gl.get_piece(row, col)

        # 当前有选中棋子
        if self.board.selected_pos:
            sel_row, sel_col = self.board.selected_pos

            # 点击同一棋子 → 取消选中
            if row == sel_row and col == sel_col:
                self.board.selected_pos = []
                self.board.valid_moves = []
                self._update_turn_display()
                return

            # 点击自己方另一个棋子 → 切换选中
            if clicked_piece and clicked_piece.color == 'red':
                self._select_piece(row, col)
                return

            # 点击目标格 → 尝试走棋
            if gl.is_valid_move(sel_row, sel_col, row, col):
                self._execute_move(sel_row, sel_col, row, col, is_ai=False)
                return
            else:
                self.status_label.text = '走棋无效，请重新选择'
                self.board.selected_pos = []
                self.board.valid_moves = []
                return

        # 没有选中棋子，尝试选中红方棋子
        if clicked_piece and clicked_piece.color == 'red':
            self._select_piece(row, col)
        else:
            self.status_label.text = '请选择红方（你的）棋子'

    def _select_piece(self, row, col):
        """选中一个棋子，显示可走位置"""
        gl = self.game_logic
        piece = gl.get_piece(row, col)
        if not piece:
            return

        self.board.selected_pos = [row, col]
        valid_moves = gl.get_valid_moves(row, col)
        self.board.valid_moves = valid_moves
        self.status_label.text = f'选中你的{piece.animal}，请点击目标格'

    def _trigger_ai_move(self):
        """触发 AI 走棋（延时 0.5 秒后执行，模拟思考）"""
        self.ai_pending = True
        Clock.schedule_once(self._ai_do_move, 0.5)

    def _ai_do_move(self, dt):
        """AI 执行走棋"""
        gl = self.game_logic

        if gl.game_over or gl.current_turn != 'blue':
            self.ai_pending = False
            return

        move = self.ai_player.get_best_move(gl)
        if move:
            (fr, fc), (tr, tc) = move
            self._execute_move(fr, fc, tr, tc, is_ai=True)
        else:
            self.status_label.text = 'AI 无合法走法，游戏结束'
            gl.game_over = True
            gl.winner = 'red'
            self._update_turn_display()
            self.ai_pending = False


class AITestApp(App):
    """AI 对战 + 音效 验证 App"""

    def build(self):
        Window.clearcolor = hex_to_rgb(COLORS['background'])

        # 窗口大小适配棋盘
        board_width = BOARD_COLS * CELL_SIZE + 40
        board_height = BOARD_ROWS * CELL_SIZE + 120
        Window.size = (board_width, board_height + 60)

        return GameScreen()


if __name__ == '__main__':
    AITestApp().run()
