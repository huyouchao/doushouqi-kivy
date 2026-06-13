"""
斗兽棋 Kivy 版
支持：登录/注册 + AI/双人对战 + 悔棋 + 计时 + 存档读档 + 积分历史 + 关于 + 动画
"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui'))

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.core.window import Window
from kivy.graphics import Color, Line, Rectangle
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.textinput import TextInput
from kivy.uix.modalview import ModalView
from kivy.uix.widget import Widget

from ai_player import AIPlayer, DIFFICULTY_PROFILES
from auth_logic import AccountStore, MASTER_PASSWORD
from auth_screen import (
    ChangePasswordScreen,
    LoginScreen,
    RegisterScreen,
    ResetPasswordScreen,
    _mk_button,
    _mk_label,
    _show_popup,
)
from board_widget import BoardWidget, CHINESE_FONT, hex_to_rgb
from constants import BOARD_COLS, BOARD_ROWS, CELL_SIZE, COLORS, RIVER_CELLS
from game_logic import GameLogic
from sound_manager import SoundManager
from platform_services.dialogs import choose_load_path, choose_save_path, list_saved_games
from platform_services.device import get_viewport_metrics, scaled, use_horizontal_game_layout
from platform_services.resources import get_desktop_icon_path
from platform_services.runtime import (
    apply_desktop_window_setup,
    center_window,
    configure_soft_input_mode,
    enable_high_dpi,
    is_android,
    supports_native_file_dialogs,
)
from platform_services.storage import get_saves_dir


SCORE_BY_DIFFICULTY = {
    "1": 0, "2": 1, "3": 3, "4": 7, "5": 12,
    "6": 20, "7": 32, "8": 50, "9": 75, "10": 100,
}
DRAW_REASON_TEXT = {
    "no_capture_limit": "长时间无吃子",
    "threefold_repetition": "局面重复",
    "manual_end": "手动结束战斗",
}
DEFAULT_WINDOW_SIZE = (1280, 860)
LOGIN_WINDOW_SIZE = (920, 700)
MIN_WINDOW_SIZE = (980, 760)
TOP_BAR_HEIGHT = 48


enable_high_dpi()


def _mk_spinner(text, values, font_size='14sp', **kwargs):
    """创建带中文字体的 Spinner。"""
    class ChineseSpinnerOption(SpinnerOption):
        def __init__(self, **kw):
            super().__init__(**kw)
            if CHINESE_FONT:
                self.font_name = CHINESE_FONT

    spinner = Spinner(
        text=text,
        values=values,
        font_size=font_size,
        option_cls=ChineseSpinnerOption,
        **kwargs,
    )
    if CHINESE_FONT:
        spinner.font_name = CHINESE_FONT
    return spinner


def _style_block(widget, bg_color=(0.11, 0.17, 0.25, 0.94),
                 border_color=(0.27, 0.37, 0.48, 1.0)):
    """给容器增加背景与边框。"""
    with widget.canvas.before:
        Color(*bg_color)
        bg = Rectangle(pos=widget.pos, size=widget.size)
        Color(*border_color)
        border = Line(rectangle=(widget.x, widget.y, widget.width, widget.height), width=1.2)

    def _sync(*_args):
        bg.pos = widget.pos
        bg.size = widget.size
        border.rectangle = (widget.x, widget.y, widget.width, widget.height)

    widget.bind(pos=_sync, size=_sync)


def _enable_wrap(label, halign='center', valign='middle'):
    """让 Label 根据宽度自动换行。"""
    label.halign = halign
    label.valign = valign

    def _sync(instance, value):
        instance.text_size = (value[0], None)

    label.bind(size=_sync)
    return label


def _section_title(text):
    return _mk_label(
        text,
        font_size='13sp',
        color=(0.77, 0.83, 0.90, 1),
        size_hint_y=None,
        height=28,
    )


def _info_caption(text):
    return _mk_label(
        text,
        font_size='11sp',
        color=(0.67, 0.74, 0.82, 1),
        size_hint_y=None,
        height=16,
    )


def _value_label(text, color=(1, 1, 1, 1), height=24):
    return _enable_wrap(_mk_label(
        text,
        font_size='13sp',
        color=color,
        size_hint_y=None,
        height=height,
    ), halign='center')


def format_duration(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def get_default_window_size():
    return DEFAULT_WINDOW_SIZE


def rich_label(text, font_size='17sp', halign='left'):
    label = Label(
        text=text,
        markup=True,
        font_size=font_size,
        color=(0.10, 0.14, 0.22, 1),
        size_hint_y=None,
    )
    if CHINESE_FONT:
        label.font_name = CHINESE_FONT
    label.halign = halign
    label.valign = 'top'

    def _sync(instance, _value):
        instance.text_size = (instance.width, None)
        instance.texture_update()
        instance.height = max(instance.texture_size[1] + 20, 40)

    label.bind(width=_sync)
    return label


class ScoreHistoryPopup(Popup):
    """积分历史弹窗。"""

    HEADERS = ['用户名', '对战时间', '对手等级', '玩家用时', 'AI用时', '当局分数', '累计积分']

    def __init__(self, account_store, username, on_changed=None, **kwargs):
        self.account_store = account_store
        self.username = username
        self.on_changed = on_changed
        self.selected_entry_id = None
        super().__init__(title='积分历史', size_hint=(0.92, 0.88), **kwargs)
        if CHINESE_FONT:
            self.title_font = CHINESE_FONT
        self.background_color = (0.12, 0.15, 0.22, 0.98)
        self.title_color = (1, 1, 1, 1)

        root = BoxLayout(orientation='vertical', spacing=10, padding=12)
        tip = _mk_label(
            '点击任意一行即可选中记录；删除记录需要输入超级密码。',
            font_size='13sp',
            color=(0.86, 0.88, 0.90, 1),
            size_hint_y=None,
            height=24,
        )
        root.add_widget(tip)

        self.table_scroll = ScrollView(
            do_scroll_x=True,
            do_scroll_y=True,
            bar_width=10,
            scroll_type=['bars', 'content'],
        )
        root.add_widget(self.table_scroll)

        bottom = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
        self.delete_btn = _mk_button(
            '删除选中记录',
            font_size='13sp',
            background_color=(0.55, 0.24, 0.24, 1),
        )
        self.delete_btn.bind(on_press=self._request_delete)
        close_btn = _mk_button(
            '关闭',
            font_size='13sp',
            background_color=(0.22, 0.46, 0.68, 1),
        )
        close_btn.bind(on_press=lambda *_: self.dismiss())
        bottom.add_widget(self.delete_btn)
        bottom.add_widget(close_btn)
        root.add_widget(bottom)

        self.content = root
        self._reload_table()

    def _measure_column_widths(self, entries):
        widths = [120, 220, 150, 140, 120, 120, 120]
        sample_rows = [self.HEADERS]
        for entry in entries:
            sample_rows.append([
                entry['username'],
                entry['played_at'],
                entry['difficulty_label'],
                format_duration(entry['player_seconds']),
                format_duration(entry['ai_seconds']),
                f"{entry['game_score']} 分",
                f"{entry['cumulative_score']} 分",
            ])
        for row in sample_rows:
            for index, text in enumerate(row):
                label = CoreLabel(
                    text=str(text),
                    font_size=16,
                    font_name=CHINESE_FONT if CHINESE_FONT else None,
                )
                label.refresh()
                widths[index] = max(widths[index], label.texture.size[0] + 42)
        return widths

    def _reload_table(self):
        entries = self.account_store.get_score_history(self.username)
        if self.selected_entry_id and not any(item['id'] == self.selected_entry_id for item in entries):
            self.selected_entry_id = None
        widths = self._measure_column_widths(entries)
        table = GridLayout(
            cols=len(self.HEADERS),
            size_hint=(None, None),
            spacing=1,
            padding=[0, 0, 0, 0],
        )
        table.bind(minimum_width=table.setter('width'), minimum_height=table.setter('height'))
        table.row_default_height = 42
        table.row_force_default = True

        for index, header in enumerate(self.HEADERS):
            header_label = Label(
                text=header,
                size_hint=(None, None),
                size=(widths[index], 42),
                color=(1, 1, 1, 1),
                bold=True,
            )
            if CHINESE_FONT:
                header_label.font_name = CHINESE_FONT
            header_label.canvas.before.clear()
            with header_label.canvas.before:
                Color(0.18, 0.28, 0.40, 1)
                Rectangle(pos=header_label.pos, size=header_label.size)
            header_label.bind(
                pos=lambda inst, *_: self._sync_cell_bg(inst),
                size=lambda inst, *_: self._sync_cell_bg(inst),
            )
            table.add_widget(header_label)

        if not entries:
            empty_values = ['当前没有积分记录', '', '', '', '', '', '']
            for index, text in enumerate(empty_values):
                cell = self._make_table_cell(text, widths[index], None, False)
                table.add_widget(cell)
        else:
            for entry in entries:
                selected = entry['id'] == self.selected_entry_id
                row_values = [
                    entry['username'],
                    entry['played_at'],
                    entry['difficulty_label'],
                    format_duration(entry['player_seconds']),
                    format_duration(entry['ai_seconds']),
                    f"{entry['game_score']} 分",
                    f"{entry['cumulative_score']} 分",
                ]
                for index, text in enumerate(row_values):
                    cell = self._make_table_cell(text, widths[index], entry['id'], selected)
                    table.add_widget(cell)

        self.table_scroll.clear_widgets()
        self.table_scroll.add_widget(table)
        self.delete_btn.disabled = self.selected_entry_id is None

    def _sync_cell_bg(self, widget):
        for instruction in widget.canvas.before.children:
            if isinstance(instruction, Rectangle):
                instruction.pos = widget.pos
                instruction.size = widget.size

    def _make_table_cell(self, text, width, entry_id, selected):
        bg_color = (0.20, 0.33, 0.51, 1) if selected else (0.12, 0.18, 0.26, 1)
        button = Button(
            text=str(text),
            size_hint=(None, None),
            size=(width, 42),
            background_normal='',
            background_down='',
            background_color=bg_color,
            color=(0.97, 0.97, 0.97, 1),
            font_size='13sp',
        )
        if CHINESE_FONT:
            button.font_name = CHINESE_FONT
        if entry_id:
            button.bind(on_press=lambda *_args, eid=entry_id: self._select_entry(eid))
        else:
            button.disabled = True
        return button

    def _select_entry(self, entry_id):
        self.selected_entry_id = entry_id
        self._reload_table()

    def _request_delete(self, *_args):
        if not self.selected_entry_id:
            _show_popup('提示', '请先选中一条积分记录。')
            return

        content = BoxLayout(orientation='vertical', spacing=10, padding=12)
        prompt = _mk_label(
            f'删除后累计积分会自动重算。\n请输入超级密码（当前为 {MASTER_PASSWORD}）：',
            font_size='14sp',
            color=(0.92, 0.92, 0.92, 1),
            size_hint_y=None,
            height=56,
        )
        pwd_input = TextInput(password=True, multiline=False, size_hint_y=None, height=40)
        if CHINESE_FONT:
            pwd_input.font_name = CHINESE_FONT
        buttons = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
        cancel_btn = _mk_button('取消', background_color=(0.38, 0.28, 0.28, 1))
        confirm_btn = _mk_button('确认删除', background_color=(0.60, 0.24, 0.24, 1))
        buttons.add_widget(cancel_btn)
        buttons.add_widget(confirm_btn)
        content.add_widget(prompt)
        content.add_widget(pwd_input)
        content.add_widget(buttons)

        popup = Popup(
            title='删除积分记录',
            content=content,
            size_hint=(0.46, 0.34),
            background_color=(0.15, 0.15, 0.22, 0.98),
            title_color=(1, 1, 1, 1),
        )
        if CHINESE_FONT:
            popup.title_font = CHINESE_FONT

        def do_delete(*_):
            try:
                self.account_store.delete_score_entry(self.selected_entry_id, pwd_input.text)
            except ValueError as exc:
                _show_popup('删除失败', str(exc))
                return
            popup.dismiss()
            self._reload_table()
            if self.on_changed:
                self.on_changed()
            _show_popup('删除成功', '积分记录已删除，累计积分已自动重算。')

        cancel_btn.bind(on_press=lambda *_: popup.dismiss())
        confirm_btn.bind(on_press=do_delete)
        popup.open()


def _format_file_size(size):
    size = max(0, int(size or 0))
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


class SavedGamesPopup(Popup):
    """非桌面平台使用的应用内存档列表弹窗。"""

    def __init__(self, save_dir, on_select, **kwargs):
        self.save_dir = save_dir
        self.on_select = on_select
        super().__init__(
            title='读取存档',
            size_hint=(0.78, 0.82),
            background_color=(0.95, 0.97, 1.0, 1),
            title_color=(0.06, 0.15, 0.32, 1),
            **kwargs,
        )
        if CHINESE_FONT:
            self.title_font = CHINESE_FONT
        self.content = self._build_content()

    def _build_content(self):
        root = BoxLayout(orientation='vertical', spacing=10, padding=12)
        tip = _mk_label(
            '请选择要读取的存档',
            font_size='14sp',
            color=(0.12, 0.18, 0.28, 1),
            size_hint_y=None,
            height=26,
        )
        root.add_widget(tip)

        entries = list_saved_games(self.save_dir)
        if not entries:
            empty_box = BoxLayout(orientation='vertical', padding=[14, 16, 14, 16])
            _style_block(empty_box, bg_color=(0.98, 0.99, 1.0, 1), border_color=(0.72, 0.78, 0.86, 1))
            empty_box.add_widget(_mk_label(
                '当前还没有可读取的存档。',
                font_size='14sp',
                color=(0.26, 0.34, 0.46, 1),
            ))
            root.add_widget(empty_box)
        else:
            scroll = ScrollView(do_scroll_x=False, do_scroll_y=True, bar_width=10)
            list_box = GridLayout(cols=1, spacing=10, size_hint_y=None, padding=[2, 2, 2, 2])
            list_box.bind(minimum_height=list_box.setter('height'))
            for entry in entries:
                card = BoxLayout(orientation='horizontal', size_hint_y=None, height=82, spacing=10, padding=[12, 10, 12, 10])
                _style_block(card, bg_color=(0.98, 0.99, 1.0, 1), border_color=(0.72, 0.78, 0.86, 1))

                info_box = BoxLayout(orientation='vertical', spacing=4)
                name_label = _enable_wrap(_mk_label(
                    entry['name'],
                    font_size='14sp',
                    color=(0.08, 0.18, 0.36, 1),
                    size_hint_y=None,
                    height=24,
                ), halign='left')
                meta_label = _enable_wrap(_mk_label(
                    f"修改时间：{entry['modified_at']}\n大小：{_format_file_size(entry['size'])}",
                    font_size='12sp',
                    color=(0.30, 0.38, 0.48, 1),
                    size_hint_y=None,
                    height=40,
                ), halign='left')
                info_box.add_widget(name_label)
                info_box.add_widget(meta_label)

                load_btn = _mk_button(
                    '读取',
                    font_size='13sp',
                    size_hint_x=None,
                    width=88,
                    background_color=(0.24, 0.47, 0.68, 1),
                    color=(1, 1, 1, 1),
                )
                load_btn.bind(on_release=lambda *_args, path=entry['path']: self._select_entry(path))

                card.add_widget(info_box)
                card.add_widget(load_btn)
                list_box.add_widget(card)

            scroll.add_widget(list_box)
            root.add_widget(scroll)

        buttons = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
        refresh_btn = _mk_button('刷新', font_size='13sp', background_color=(0.29, 0.42, 0.56, 1))
        close_btn = _mk_button('关闭', font_size='13sp', background_color=(0.42, 0.32, 0.32, 1))
        refresh_btn.bind(on_release=lambda *_args: self._refresh_content())
        close_btn.bind(on_release=lambda *_args: self.dismiss())
        buttons.add_widget(refresh_btn)
        buttons.add_widget(close_btn)
        root.add_widget(buttons)
        return root

    def _refresh_content(self):
        self.content = self._build_content()

    def _select_entry(self, filepath):
        self.dismiss()
        if self.on_select:
            Clock.schedule_once(lambda _dt: self.on_select(filepath), 0)


class SaveGamePopup(Popup):
    """非桌面平台使用的应用内保存弹窗。"""

    def __init__(self, save_dir, suggested_name, on_confirm, **kwargs):
        self.save_dir = save_dir
        self.suggested_name = suggested_name
        self.on_confirm = on_confirm
        super().__init__(
            title='保存对局',
            size_hint=(0.72, 0.50),
            background_color=(0.95, 0.97, 1.0, 1),
            title_color=(0.06, 0.15, 0.32, 1),
            **kwargs,
        )
        if CHINESE_FONT:
            self.title_font = CHINESE_FONT
        self.content = self._build_content()

    def _build_content(self):
        root = BoxLayout(orientation='vertical', spacing=10, padding=12)
        tip = _mk_label(
            '请输入存档名称，文件将保存到应用内部存档目录。',
            font_size='14sp',
            color=(0.12, 0.18, 0.28, 1),
            size_hint_y=None,
            height=26,
        )
        root.add_widget(tip)

        input_box = BoxLayout(orientation='vertical', spacing=8, size_hint_y=None, height=104, padding=[10, 10, 10, 10])
        _style_block(input_box, bg_color=(0.98, 0.99, 1.0, 1), border_color=(0.72, 0.78, 0.86, 1))
        input_box.add_widget(_mk_label(
            f'保存目录：{self.save_dir}',
            font_size='12sp',
            color=(0.27, 0.35, 0.46, 1),
            size_hint_y=None,
            height=22,
        ))
        self.filename_input = TextInput(
            text=self.suggested_name,
            multiline=False,
            size_hint_y=None,
            height=40,
            font_size='15sp',
        )
        if CHINESE_FONT:
            self.filename_input.font_name = CHINESE_FONT
        self.filename_input.bind(on_text_validate=lambda *_args: self._confirm())
        input_box.add_widget(self.filename_input)
        root.add_widget(input_box)

        buttons = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
        cancel_btn = _mk_button('取消', font_size='13sp', background_color=(0.42, 0.32, 0.32, 1))
        save_btn = _mk_button('保存', font_size='13sp', background_color=(0.24, 0.47, 0.68, 1))
        cancel_btn.bind(on_release=lambda *_args: self.dismiss())
        save_btn.bind(on_release=lambda *_args: self._confirm())
        buttons.add_widget(cancel_btn)
        buttons.add_widget(save_btn)
        root.add_widget(buttons)
        return root

    def _confirm(self):
        filename = self.filename_input.text.strip()
        if not filename:
            _show_popup('提示', '请输入存档名称')
            return
        self.dismiss()
        if self.on_confirm:
            Clock.schedule_once(lambda _dt: self.on_confirm(filename), 0)


class GameScreen(Screen):
    """响应式主界面。"""

    def __init__(self, username='', account_store=None, **kwargs):
        super().__init__(**kwargs)
        self.username = username
        self.account_store = account_store

        self.game_logic = GameLogic()
        self.ai_player = AIPlayer(color='blue', difficulty='5')
        self.sound_manager = SoundManager()
        self.ai_pending = False
        self.timer_event = None
        self.timer_paused = False
        self.red_seconds = 0
        self.blue_seconds = 0
        self.state_history = [self.game_logic.to_dict()]
        self.game_recorded = False
        self.current_difficulty = '5'
        self.battle_mode = 'ai'
        self.latest_game_score = None
        self.latest_game_score_text = ''
        self._suppress_spinner_callback = False
        self.active_mobile_tab = 'info'
        self._using_mobile_portrait_layout = False

        self._build_ui()
        self._sync_pieces()
        self._update_turn_display()
        self._refresh_score_labels()
        self._update_time_labels()
        self._start_timer()
        Clock.schedule_once(lambda *_: self._update_responsive_layout(), 0)

    def _build_ui(self):
        root = BoxLayout(orientation='vertical', padding=12, spacing=12)
        self.root_layout = root

        self.top_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=TOP_BAR_HEIGHT, spacing=10)
        _style_block(self.top_bar, bg_color=(0.09, 0.15, 0.23, 0.98))

        app_title = _mk_label('斗兽棋', font_size='22sp', color=hex_to_rgb('#FFD700'), size_hint_x=0.25)
        self.top_user_label = _mk_label(
            f'当前用户：{self.username}',
            font_size='14sp',
            color=(0.92, 0.93, 0.94, 1),
            size_hint_x=0.55,
        )
        self.menu_btn = _mk_button('菜单 ▼', font_size='13sp', size_hint_x=0.20, background_color=(0.22, 0.36, 0.52, 1))
        self.menu_btn.bind(on_press=self._open_menu)
        self.top_bar.add_widget(app_title)
        self.top_bar.add_widget(self.top_user_label)
        self.top_bar.add_widget(self.menu_btn)

        self.body = BoxLayout(orientation='horizontal', spacing=12)
        self.board_shell = BoxLayout(orientation='vertical', padding=10)
        _style_block(self.board_shell, bg_color=(0.08, 0.13, 0.18, 0.98))
        self.board = BoardWidget()
        self.board.cell_size = CELL_SIZE
        self.board.board_margin = 16
        self.board.on_cell_click = self._on_cell_click
        self.board_shell.add_widget(self.board)

        self.panel_scroll = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True,
            bar_width=10,
            scroll_type=['bars', 'content'],
        )
        self.side_panel = BoxLayout(
            orientation='vertical',
            spacing=8,
            size_hint=(1, 1),
        )
        self.panel_content = BoxLayout(
            orientation='vertical',
            spacing=8,
            padding=[0, 0, 0, 0],
            size_hint=(1, None),
        )
        self.panel_content.bind(minimum_height=self.panel_content.setter('height'))
        self.panel_scroll.add_widget(self.panel_content)

        self.mobile_panel = BoxLayout(
            orientation='vertical',
            spacing=8,
            size_hint=(1, 1),
        )
        self.mobile_tabs_bar = GridLayout(cols=3, size_hint_y=None, height=40, spacing=8)
        self.mobile_tab_buttons = {}
        for tab_key, title in [('info', '对局信息'), ('settings', '对局设置'), ('actions', '常用操作')]:
            btn = ToggleButton(
                text=title,
                group='mobile_panel_tab',
                allow_no_selection=False,
                font_size='13sp',
                background_normal='',
                background_down='',
                background_color=(0.22, 0.36, 0.52, 1),
                color=(0.92, 0.95, 0.97, 1),
            )
            if CHINESE_FONT:
                btn.font_name = CHINESE_FONT
            btn.bind(on_release=lambda instance, key=tab_key: self._switch_mobile_tab(key))
            self.mobile_tab_buttons[tab_key] = btn
            self.mobile_tabs_bar.add_widget(btn)
        _style_block(self.mobile_tabs_bar, bg_color=(0.10, 0.15, 0.22, 0.98), border_color=(0.22, 0.30, 0.40, 1.0))
        self.mobile_panel.add_widget(self.mobile_tabs_bar)
        self.mobile_content_host = BoxLayout(orientation='vertical', size_hint=(1, 1))
        self.mobile_panel.add_widget(self.mobile_content_host)

        self.turn_block = BoxLayout(orientation='vertical', size_hint_y=None, height=96, padding=[14, 12, 14, 12], spacing=6)
        _style_block(self.turn_block)
        self.turn_label = _mk_label('红方回合', font_size='18sp', color=hex_to_rgb(COLORS['red_piece']), size_hint_y=None, height=28)
        self.status_label = _enable_wrap(_mk_label('请点击红方棋子', font_size='12sp', color=hex_to_rgb(COLORS['board_line']), size_hint_y=None, height=36), halign='center')
        self.turn_block.add_widget(self.turn_label)
        self.turn_block.add_widget(self.status_label)

        self.info_block = BoxLayout(orientation='vertical', size_hint_y=None, height=270, padding=[14, 14, 14, 14], spacing=10)
        _style_block(self.info_block)
        self.info_block.add_widget(_section_title('对局信息'))
        self.info_list = GridLayout(cols=1, size_hint_y=None, height=196, spacing=6)

        self.user_value_label = self._make_info_line('当前用户：', height=24)
        self.step_label = self._make_info_line('当前步数：', height=24)
        self.player_time_label = self._make_info_line('', color=hex_to_rgb(COLORS['red_piece']), height=24)
        self.opponent_time_label = self._make_info_line('', color=hex_to_rgb(COLORS['blue_piece']), height=24)
        self.local_score_label = self._make_info_line('本局分数：', color=(0.98, 0.93, 0.60, 1), height=36)
        self.total_score_label = self._make_info_line('累计积分：', color=hex_to_rgb('#FFD700'), height=24)

        for widget in [
            self.user_value_label,
            self.step_label,
            self.player_time_label,
            self.opponent_time_label,
            self.local_score_label,
            self.total_score_label,
        ]:
            self.info_list.add_widget(widget)
        self.info_block.add_widget(self.info_list)

        self.settings_block = BoxLayout(orientation='vertical', size_hint_y=None, height=144, padding=[14, 20, 14, 14], spacing=10)
        _style_block(self.settings_block)
        self.settings_block.add_widget(_section_title('对局设置'))

        mode_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=34, spacing=8)
        self.mode_label = _mk_label('模式:', font_size='13sp', color=(0.74, 0.82, 0.92, 1), size_hint_x=0.18)
        mode_row.add_widget(self.mode_label)
        self.mode_spinner = _mk_spinner(
            '人机对战',
            ['人机对战', '双人对战'],
            font_size='13sp',
            size_hint_x=0.82,
            background_color=(0.30, 0.35, 0.50, 1),
            color=(1, 1, 1, 1),
        )
        self.mode_spinner.bind(text=self._on_mode_change)
        mode_row.add_widget(self.mode_spinner)

        diff_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=34, spacing=8)
        self.diff_label = _mk_label('难度:', font_size='13sp', color=(0.74, 0.82, 0.92, 1), size_hint_x=0.18)
        diff_row.add_widget(self.diff_label)
        self.difficulty_spinner = _mk_spinner(
            DIFFICULTY_PROFILES['5']['label'],
            [DIFFICULTY_PROFILES[key]['label'] for key in DIFFICULTY_PROFILES],
            font_size='13sp',
            size_hint_x=0.82,
            background_color=hex_to_rgb(COLORS['den_blue']),
            color=(1, 1, 1, 1),
        )
        self.difficulty_spinner.bind(text=self._on_difficulty_change)
        diff_row.add_widget(self.difficulty_spinner)
        self.settings_block.add_widget(mode_row)
        self.settings_block.add_widget(diff_row)

        self.actions_block = BoxLayout(orientation='vertical', size_hint_y=None, height=114, padding=[14, 16, 14, 12], spacing=6)
        _style_block(self.actions_block)
        self.actions_block.add_widget(_section_title('常用操作'))
        self.action_box = BoxLayout(orientation='vertical', size_hint_y=None, height=72, spacing=6)
        self.action_row_top = GridLayout(cols=2, size_hint_y=None, height=32, spacing=[8, 8])
        self.action_row_bottom = BoxLayout(orientation='horizontal', size_hint_y=None, height=32, spacing=8)

        self.sound_btn = _mk_button('音效:开', font_size='13sp', background_color=(0.22, 0.62, 0.24, 1), color=(1, 1, 1, 1))
        self.sound_btn.bind(on_press=self._on_toggle_sound)

        action_defs = [
            ('新游戏', self._on_new_game, hex_to_rgb(COLORS['den_blue'])),
            ('悔棋', self._on_undo, (0.42, 0.34, 0.24, 1)),
            ('音效:开', self._on_toggle_sound, (0.22, 0.62, 0.24, 1)),
        ]
        for text, callback, bg_color in action_defs[:2]:
            btn = _mk_button(text, font_size='13sp', background_color=bg_color, color=(1, 1, 1, 1))
            btn.bind(on_press=callback)
            self.action_row_top.add_widget(btn)
        self.action_row_bottom.add_widget(Widget(size_hint_x=0.16))
        self.sound_btn.size_hint_x = 0.68
        self.action_row_bottom.add_widget(self.sound_btn)
        self.action_row_bottom.add_widget(Widget(size_hint_x=0.16))
        self.action_box.add_widget(self.action_row_top)
        self.action_box.add_widget(self.action_row_bottom)
        self.actions_block.add_widget(self.action_box)

        self.panel_content.add_widget(self.turn_block)
        self.panel_content.add_widget(self.info_block)
        self.panel_content.add_widget(self.settings_block)

        self.side_panel.add_widget(self.panel_scroll)
        self.side_panel.add_widget(self.actions_block)

        self.body.add_widget(self.board_shell)
        self.body.add_widget(self.side_panel)

        root.add_widget(self.top_bar)
        root.add_widget(self.body)
        self.add_widget(root)

        self.bind(size=lambda *_: self._update_responsive_layout())
        self.board_shell.bind(size=lambda *_: self._update_board_scale())

    def _make_info_line(self, prefix, color=(1, 1, 1, 1), height=26):
        label = _enable_wrap(_mk_label(prefix, font_size='11sp', color=color, size_hint_y=None, height=height), halign='left')
        label.padding = (6, 0)
        _style_block(label, bg_color=(0.10, 0.15, 0.22, 1.0), border_color=(0.22, 0.30, 0.40, 1))
        return label

    def _update_responsive_layout(self):
        metrics = get_viewport_metrics((self.width, self.height))
        body_width = max(1, self.width - scaled(24, metrics, min_value=16))
        body_height = max(1, self.height - scaled(TOP_BAR_HEIGHT + 36, metrics, min_value=72))
        use_horizontal = use_horizontal_game_layout((body_width, body_height))
        is_portrait = not metrics.is_landscape
        is_compact_portrait = is_portrait and metrics.breakpoint == 'compact'
        use_mobile_portrait = is_portrait and not metrics.is_tablet_like

        outer_gap = scaled(10, metrics, min_value=6, max_value=18)
        self.root_layout.padding = outer_gap
        self.root_layout.spacing = outer_gap
        self.body.spacing = outer_gap
        self.side_panel.spacing = block_spacing = scaled(5, metrics, min_value=3, max_value=8)
        self.mobile_panel.spacing = block_spacing
        self.top_bar.height = scaled(TOP_BAR_HEIGHT + (8 if use_mobile_portrait else 0), metrics, min_value=48, max_value=72)
        self.top_bar.spacing = scaled(10, metrics, min_value=8, max_value=16)
        self.board_shell.padding = scaled(8 if use_horizontal else 10, metrics, min_value=6, max_value=16)
        self.top_user_label.size_hint_x = 0.50 if use_horizontal else (0.48 if use_mobile_portrait else 0.44)
        self.menu_btn.size_hint_x = 0.22 if use_horizontal else (0.22 if use_mobile_portrait else 0.24)

        block_padding_x = scaled(12, metrics, min_value=8, max_value=18)
        block_padding_y = scaled(10, metrics, min_value=6, max_value=14)
        self.turn_block.height = scaled(82 if use_mobile_portrait else (90 if is_portrait else 96), metrics, min_value=76, max_value=136)
        self.turn_block.padding = [block_padding_x, block_padding_y, block_padding_x, block_padding_y]
        self.turn_block.spacing = block_spacing
        self.info_block.height = scaled(236 if use_mobile_portrait else (258 if is_portrait else 248), metrics, min_value=208, max_value=340)
        self.info_block.padding = [block_padding_x, block_padding_x, block_padding_x, block_padding_x]
        self.info_block.spacing = scaled(8, metrics, min_value=4, max_value=12)
        self.info_list.spacing = block_spacing
        self.info_list.height = self.info_block.height - scaled(56, metrics, min_value=48, max_value=72)
        self.settings_block.height = scaled(136 if use_mobile_portrait else (132 if is_portrait else 134), metrics, min_value=122, max_value=184)
        self.settings_block.padding = [block_padding_x, block_padding_x, block_padding_x, block_padding_x]
        self.settings_block.spacing = scaled(8, metrics, min_value=4, max_value=12)
        self.actions_block.height = scaled(122 if use_mobile_portrait else (108 if is_portrait else 110), metrics, min_value=98, max_value=152)
        self.actions_block.padding = [block_padding_x, block_padding_y, block_padding_x, block_padding_y]
        self.actions_block.spacing = block_spacing
        self.action_box.height = scaled(76 if use_mobile_portrait else 64, metrics, min_value=58, max_value=92)
        self.action_row_top.height = scaled(34 if use_mobile_portrait else 28, metrics, min_value=26, max_value=42)
        self.action_row_bottom.height = scaled(34 if use_mobile_portrait else 28, metrics, min_value=26, max_value=42)
        row_gap = scaled(5, metrics, min_value=3, max_value=8)
        self.action_box.spacing = row_gap
        self.action_row_top.spacing = [row_gap, row_gap]
        self.action_row_bottom.spacing = row_gap
        self.mobile_tabs_bar.height = scaled(40, metrics, min_value=36, max_value=52)
        self.mobile_tabs_bar.spacing = row_gap
        label_ratio = 0.16 if use_horizontal else 0.15
        spinner_ratio = 1.0 - label_ratio
        self.mode_label.size_hint_x = label_ratio
        self.diff_label.size_hint_x = label_ratio
        self.mode_spinner.size_hint_x = spinner_ratio
        self.difficulty_spinner.size_hint_x = spinner_ratio

        self._apply_panel_layout_mode(use_mobile_portrait)
        if use_horizontal:
            self.body.orientation = 'horizontal'
            self.board_shell.size_hint = (0.78, 1)
            self.side_panel.size_hint = (0.22, 1)
            self.panel_scroll.size_hint = (1, 1)
            self.actions_block.size_hint_y = None
            self.panel_scroll.height = max(120, body_height - self.actions_block.height - self.side_panel.spacing)
        else:
            self.body.orientation = 'vertical'
            self.side_panel.size_hint = (1, 1)
            self.actions_block.size_hint_y = None
            if use_mobile_portrait:
                self.board_shell.size_hint = (1, 0.74)
                self.side_panel.size_hint = (1, 0.26)
                self.panel_scroll.size_hint = (1, 1)
                self.panel_scroll.height = max(110, body_height * 0.26 - self.actions_block.height - self.side_panel.spacing)
            elif is_compact_portrait:
                self.board_shell.size_hint = (1, 0.66)
                self.side_panel.size_hint = (1, 0.34)
                self.panel_scroll.size_hint = (1, 1)
                self.panel_scroll.height = max(96, body_height * 0.34 - self.actions_block.height - self.side_panel.spacing)
            elif is_portrait:
                self.board_shell.size_hint = (1, 0.68)
                self.side_panel.size_hint = (1, 0.32)
                self.panel_scroll.size_hint = (1, 1)
                self.panel_scroll.height = max(96, body_height * 0.32 - self.actions_block.height - self.side_panel.spacing)
            else:
                self.board_shell.size_hint = (1, 0.64)
                self.side_panel.size_hint = (1, 0.36)
                self.panel_scroll.size_hint = (1, 1)
                self.panel_scroll.height = max(110, body_height * 0.36 - self.actions_block.height - self.side_panel.spacing)

        self._update_board_scale()

    def _update_board_scale(self):
        metrics = get_viewport_metrics((self.width, self.height))
        available_w = max(320, self.board_shell.width - scaled(28, metrics, min_value=20, max_value=34))
        available_h = max(320, self.board_shell.height - scaled(28, metrics, min_value=20, max_value=34))
        cell_by_w = available_w / BOARD_COLS
        cell_by_h = available_h / BOARD_ROWS
        if metrics.is_landscape and metrics.is_tablet_like:
            max_cell = 96
        elif metrics.is_landscape:
            max_cell = 88
        else:
            if not metrics.is_tablet_like:
                max_cell = 112 if metrics.breakpoint == 'compact' else 120
            else:
                max_cell = 82 if metrics.breakpoint == 'compact' else 86
        min_cell = 34 if metrics.breakpoint == 'compact' else 38
        new_size = max(min_cell, min(max_cell, int(min(cell_by_w, cell_by_h))))
        self.board.cell_size = new_size
        self.board.board_margin = max(12, int(new_size * 0.22))

    def _apply_panel_layout_mode(self, use_mobile_portrait):
        if self._using_mobile_portrait_layout == use_mobile_portrait:
            return
        self._using_mobile_portrait_layout = use_mobile_portrait

        for parent, child in [
            (self.panel_content, self.turn_block),
            (self.panel_content, self.info_block),
            (self.panel_content, self.settings_block),
            (self.side_panel, self.panel_scroll),
            (self.side_panel, self.actions_block),
            (self.mobile_content_host, self.turn_block),
            (self.mobile_content_host, self.info_block),
            (self.mobile_content_host, self.settings_block),
            (self.mobile_content_host, self.actions_block),
            (self.side_panel, self.mobile_panel),
        ]:
            if child.parent is parent:
                parent.remove_widget(child)

        if use_mobile_portrait:
            self.side_panel.add_widget(self.mobile_panel)
            self._switch_mobile_tab(self.active_mobile_tab)
        else:
            self.panel_content.add_widget(self.turn_block)
            self.panel_content.add_widget(self.info_block)
            self.panel_content.add_widget(self.settings_block)
            self.side_panel.add_widget(self.panel_scroll)
            self.side_panel.add_widget(self.actions_block)

    def _switch_mobile_tab(self, tab_key):
        self.active_mobile_tab = tab_key
        active_bg = (0.24, 0.50, 0.76, 1)
        inactive_bg = (0.16, 0.25, 0.35, 1)
        for key, btn in self.mobile_tab_buttons.items():
            is_active = key == tab_key
            btn.state = 'down' if is_active else 'normal'
            btn.background_color = active_bg if is_active else inactive_bg

        if not hasattr(self, 'mobile_content_host') or not self._using_mobile_portrait_layout:
            return

        for child in list(self.mobile_content_host.children):
            self.mobile_content_host.remove_widget(child)

        content_map = {
            'info': [self.turn_block, self.info_block],
            'settings': [self.settings_block],
            'actions': [self.actions_block],
        }
        for widget in content_map.get(tab_key, [self.turn_block, self.info_block]):
            if widget.parent is not None and widget.parent is not self.mobile_content_host:
                widget.parent.remove_widget(widget)
            if widget.parent is not self.mobile_content_host:
                self.mobile_content_host.add_widget(widget)

    def _open_menu(self, *_args):
        dropdown = DropDown(auto_width=False, width=240)
        _style_block(dropdown, bg_color=(0.10, 0.14, 0.20, 1.0), border_color=(0.28, 0.36, 0.48, 1.0))

        def add_header(text):
            header = _mk_button(
                text,
                font_size='12sp',
                size_hint_y=None,
                height=30,
                background_color=(0.16, 0.22, 0.30, 1),
                color=(0.85, 0.90, 0.95, 1),
                background_normal='',
                background_down='',
            )
            header.disabled = True
            dropdown.add_widget(header)

        def add_item(text, callback, color):
            item = _mk_button(
                text,
                font_size='13sp',
                size_hint_y=None,
                height=36,
                background_color=color,
                background_normal='',
                background_down='',
            )
            def _trigger_action(*_args):
                dropdown.dismiss()
                Clock.schedule_once(lambda _dt: callback(None), 0)

            item.bind(on_release=_trigger_action)
            dropdown.add_widget(item)

        add_header('对局')
        add_item('存档', self._on_save, (0.24, 0.45, 0.35, 1))
        add_item('读档', self._on_load, (0.24, 0.45, 0.35, 1))
        add_item('结束当前对局', self._on_end_game, (0.55, 0.33, 0.22, 1))

        add_header('数据')
        add_item('积分历史', self._show_score_history, (0.25, 0.38, 0.58, 1))

        add_header('窗口')
        add_item('记住当前窗口大小', self._remember_window_size, (0.26, 0.40, 0.58, 1))
        add_item('恢复默认窗口大小', self._restore_default_window_size, (0.30, 0.36, 0.46, 1))

        add_header('帮助')
        add_item('关于', self._show_about, (0.20, 0.46, 0.35, 1))
        add_item('退出登录', self._on_logout, (0.56, 0.28, 0.22, 1))

        dropdown.open(self.menu_btn)

    def _show_about(self, *_args):
        content_text = (
            "[color=#082b66][b]软件功能[/b][/color]\n"
            "[color=#1f2937]1. 支持登录、注册、修改密码与超级密码找回。\n"
            "2. 支持人机对战、双人对战、悔棋、计时、音效、存档与读档。\n"
            "3. 支持积分累计、积分历史查询、删除积分记录与窗口尺寸记忆。[/color]\n\n"
            "[color=#5b1f00][b]使用说明[/b][/color]\n"
            "[color=#3b2f2f]1. 登录后可在右侧设置对战模式和 AI 难度。\n"
            "2. 人机模式下，未结算前会显示“胜利可得分数”。\n"
            "3. 可通过“菜单”或“积分历史”按钮查看积分记录。[/color]\n\n"
            "[color=#0f5132][b]注意事项[/b][/color]\n"
            "[color=#243b30]1. 手动结束战斗、和棋、失败均为 0 分。\n"
            "2. 删除积分记录必须输入超级密码，并会自动重算累计积分。\n"
            "3. 建议在 Windows 环境下使用，以获得更好的 DPI 适配效果。[/color]\n\n"
            "[color=#4a1d96][b]平台与作者信息[/b][/color]\n"
            "[color=#312e81]平台：Vs code+Python\n"
            "作者：胡有朝\n"
            "联系方式：\n"
            "QQ：35037857\n"
            "E-mail：35037857@qq.com\n"
            "huyouchao2000@163.com\n"
            "更新日期：2026年6月13日[/color]"
        )

        root = BoxLayout(orientation='vertical', spacing=10, padding=12)
        text_panel = BoxLayout(orientation='vertical', padding=[14, 12, 14, 12])
        _style_block(text_panel, bg_color=(0.99, 0.995, 1.0, 1), border_color=(0.58, 0.66, 0.78, 1))
        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True, bar_width=10)
        text_label = rich_label(content_text)
        scroll.add_widget(text_label)
        text_panel.add_widget(scroll)
        close_btn = _mk_button('关闭', font_size='13sp', size_hint_y=None, height=40, background_color=(0.22, 0.46, 0.68, 1))
        root.add_widget(text_panel)
        root.add_widget(close_btn)

        popup = Popup(
            title='关于',
            content=root,
            size_hint=(0.70, 0.78),
            background_color=(0.94, 0.96, 0.99, 1),
            title_color=(0.05, 0.14, 0.31, 1),
        )
        if CHINESE_FONT:
            popup.title_font = CHINESE_FONT
        close_btn.bind(on_press=lambda *_: popup.dismiss())
        popup.open()

    def _show_score_history(self, *_args):
        popup = ScoreHistoryPopup(self.account_store, self.username, on_changed=self._refresh_score_labels)
        popup.open()

    def _refresh_score_labels(self):
        self.top_user_label.text = f'当前用户：{self.username}'
        self.user_value_label.text = f'当前用户：{self.username}'
        self.step_label.text = f'当前步数：第{len(self.state_history) - 1}步'
        self.total_score_label.text = f'累计积分：{self.account_store.get_total_score(self.username)} 分'

        if self.game_logic.game_over and self.latest_game_score_text:
            self.local_score_label.text = f'本局分数：{self.latest_game_score_text}'
            return

        if self.battle_mode != 'ai':
            self.local_score_label.text = '本局分数：本局 0 分（双人模式不计分）'
            return

        pending = SCORE_BY_DIFFICULTY.get(self.current_difficulty, 0)
        self.local_score_label.text = f'本局分数：待结算（胜利可得 {pending} 分）'

    def _update_time_labels(self):
        if self.battle_mode == 'ai':
            self.player_time_label.text = f'{self.username}：{format_duration(self.red_seconds)}'
            self.opponent_time_label.text = f'AI：{format_duration(self.blue_seconds)}'
        else:
            self.player_time_label.text = f'红方：{format_duration(self.red_seconds)}'
            self.opponent_time_label.text = f'蓝方：{format_duration(self.blue_seconds)}'

    def _draw_reason_label(self, reason):
        return DRAW_REASON_TEXT.get(reason, reason or '和棋')

    def _get_default_save_dir(self):
        return get_saves_dir()

    def _is_game_in_progress(self):
        return (not self.game_logic.game_over) and (len(self.state_history) > 1 or self.red_seconds > 0 or self.blue_seconds > 0)

    def _confirm_manual_end(self, then_callback):
        content = BoxLayout(orientation='vertical', spacing=10, padding=12)
        text = _mk_label(
            '当前对局尚未结束。\n继续操作会按“手动结束战斗 0 分”处理，是否继续？',
            font_size='14sp',
            color=(0.94, 0.94, 0.94, 1),
            size_hint_y=None,
            height=60,
        )
        buttons = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
        cancel_btn = _mk_button('取消', background_color=(0.40, 0.30, 0.30, 1))
        confirm_btn = _mk_button('继续', background_color=(0.55, 0.33, 0.22, 1))
        buttons.add_widget(cancel_btn)
        buttons.add_widget(confirm_btn)
        content.add_widget(text)
        content.add_widget(buttons)

        popup = Popup(
            title='确认操作',
            content=content,
            size_hint=(0.48, 0.30),
            background_color=(0.14, 0.15, 0.22, 0.98),
            title_color=(1, 1, 1, 1),
        )
        if CHINESE_FONT:
            popup.title_font = CHINESE_FONT

        def do_confirm(*_):
            popup.dismiss()
            self._finish_manual_end()
            then_callback()

        cancel_btn.bind(on_press=lambda *_: popup.dismiss())
        confirm_btn.bind(on_press=do_confirm)
        popup.open()

    def _finish_manual_end(self):
        if self.game_logic.game_over:
            return
        self.game_logic.game_over = True
        self.game_logic.winner = None
        self.game_logic.draw_reason = 'manual_end'
        self.ai_pending = False
        self._stop_timer()
        self._update_turn_display()
        self._finalize_game_result(feedback=False)

    def _start_new_game(self, status_text=''):
        self._stop_timer()
        self.game_logic = GameLogic()
        self.ai_pending = False
        self.red_seconds = 0
        self.blue_seconds = 0
        self.timer_paused = False
        self.game_recorded = False
        self.latest_game_score = None
        self.latest_game_score_text = ''
        self.state_history = [self.game_logic.to_dict()]
        self.board.selected_pos = []
        self.board.valid_moves = []
        self.board.last_move_from = []
        self.board.last_move_to = []
        self._sync_pieces()
        self._update_turn_display()
        if status_text:
            self.status_label.text = status_text
        self._refresh_score_labels()
        self._update_time_labels()
        self._start_timer()

    def _restart_for_setting_change(self, apply_change):
        if self._is_game_in_progress():
            self._confirm_manual_end(lambda: self._apply_setting_and_restart(apply_change))
        else:
            self._apply_setting_and_restart(apply_change)

    def _apply_setting_and_restart(self, apply_change):
        apply_change()
        self._start_new_game('设置已更新，已开始新对局')

    def _on_mode_change(self, spinner, text):
        if self._suppress_spinner_callback:
            return
        new_mode = 'ai' if text == '人机对战' else 'pvp'
        if new_mode == self.battle_mode:
            return

        old_text = '人机对战' if self.battle_mode == 'ai' else '双人对战'

        def apply_change():
            self.battle_mode = new_mode
            self.ai_pending = False
            self._refresh_score_labels()

        if self._is_game_in_progress():
            def revert():
                self._suppress_spinner_callback = True
                self.mode_spinner.text = old_text
                self._suppress_spinner_callback = False

            content = BoxLayout(orientation='vertical', spacing=10, padding=12)
            text_label = _mk_label(
                '切换模式将按“手动结束战斗 0 分”处理当前对局，并重新开始。是否继续？',
                font_size='14sp',
                color=(0.94, 0.94, 0.94, 1),
                size_hint_y=None,
                height=70,
            )
            buttons = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
            cancel_btn = _mk_button('取消', background_color=(0.40, 0.30, 0.30, 1))
            confirm_btn = _mk_button('继续', background_color=(0.25, 0.45, 0.62, 1))
            buttons.add_widget(cancel_btn)
            buttons.add_widget(confirm_btn)
            content.add_widget(text_label)
            content.add_widget(buttons)
            popup = Popup(
                title='切换模式',
                content=content,
                size_hint=(0.50, 0.32),
                background_color=(0.14, 0.15, 0.22, 0.98),
                title_color=(1, 1, 1, 1),
            )
            if CHINESE_FONT:
                popup.title_font = CHINESE_FONT

            cancel_btn.bind(on_press=lambda *_: (popup.dismiss(), revert()))
            confirm_btn.bind(on_press=lambda *_: (popup.dismiss(), self._finish_manual_end(), apply_change(), self._start_new_game('模式已切换')))
            popup.open()
            return

        apply_change()
        self._update_turn_display()

    def _on_difficulty_change(self, spinner, text):
        if self._suppress_spinner_callback:
            return

        new_level = None
        for key, value in DIFFICULTY_PROFILES.items():
            if value['label'] == text:
                new_level = key
                break
        if not new_level or new_level == self.current_difficulty:
            return

        old_text = DIFFICULTY_PROFILES[self.current_difficulty]['label']

        def apply_change():
            self.current_difficulty = new_level
            self.ai_player.set_difficulty(new_level)
            self._refresh_score_labels()

        if self.battle_mode == 'ai' and self._is_game_in_progress():
            content = BoxLayout(orientation='vertical', spacing=10, padding=12)
            text_label = _mk_label(
                '切换难度将按“手动结束战斗 0 分”处理当前对局，并重新开始。是否继续？',
                font_size='14sp',
                color=(0.94, 0.94, 0.94, 1),
                size_hint_y=None,
                height=70,
            )
            buttons = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
            cancel_btn = _mk_button('取消', background_color=(0.40, 0.30, 0.30, 1))
            confirm_btn = _mk_button('继续', background_color=(0.25, 0.45, 0.62, 1))
            buttons.add_widget(cancel_btn)
            buttons.add_widget(confirm_btn)
            content.add_widget(text_label)
            content.add_widget(buttons)
            popup = Popup(
                title='切换难度',
                content=content,
                size_hint=(0.50, 0.32),
                background_color=(0.14, 0.15, 0.22, 0.98),
                title_color=(1, 1, 1, 1),
            )
            if CHINESE_FONT:
                popup.title_font = CHINESE_FONT

            def revert(*_):
                popup.dismiss()
                self._suppress_spinner_callback = True
                self.difficulty_spinner.text = old_text
                self._suppress_spinner_callback = False

            def confirm(*_):
                popup.dismiss()
                self._finish_manual_end()
                apply_change()
                self._start_new_game('难度已切换')

            cancel_btn.bind(on_press=revert)
            confirm_btn.bind(on_press=confirm)
            popup.open()
            return

        apply_change()
        self.status_label.text = f'难度已设为：{text}'

    def _start_timer(self):
        if self.timer_event:
            return
        self.timer_event = Clock.schedule_interval(self._tick_timer, 1.0)

    def _stop_timer(self):
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None

    def _tick_timer(self, _dt):
        if self.timer_paused or self.game_logic.game_over:
            return
        if self.game_logic.current_turn == 'red':
            self.red_seconds += 1
        else:
            self.blue_seconds += 1
        self._update_time_labels()

    def _sync_pieces(self):
        pieces = []
        for row in range(BOARD_ROWS):
            for col in range(BOARD_COLS):
                piece = self.game_logic.get_piece(row, col)
                if piece:
                    pieces.append((piece.row, piece.col, piece.color, piece.animal))
        self.board.pieces_data = pieces

    def _update_turn_display(self):
        gl = self.game_logic
        if gl.game_over:
            self.turn_label.text = '游戏结束'
            self.turn_label.color = hex_to_rgb('#FFD700')
            if gl.winner:
                winner_name = '玩家胜利' if gl.winner == 'red' and self.battle_mode == 'ai' else ('红方胜利' if gl.winner == 'red' else ('AI胜利' if self.battle_mode == 'ai' else '蓝方胜利'))
                self.status_label.text = winner_name
            else:
                self.status_label.text = f'本局结束：{self._draw_reason_label(gl.draw_reason)}'
            return

        if gl.current_turn == 'red':
            suffix = '（你）' if self.battle_mode == 'ai' else ''
            self.turn_label.text = f'红方回合{suffix}'
            self.turn_label.color = hex_to_rgb(COLORS['red_piece'])
            self.status_label.text = '请点击红方棋子'
        else:
            suffix = '（AI）' if self.battle_mode == 'ai' else ''
            self.turn_label.text = f'蓝方回合{suffix}'
            self.turn_label.color = hex_to_rgb(COLORS['blue_piece'])
            self.status_label.text = 'AI 思考中...' if self.battle_mode == 'ai' else '请点击蓝方棋子'

    def _on_new_game(self, *_args):
        if self._is_game_in_progress():
            self._confirm_manual_end(lambda: self._start_new_game('已开始新对局'))
            return
        self._start_new_game('已开始新对局')

    def _on_end_game(self, *_args):
        if self.game_logic.game_over:
            _show_popup('提示', '当前对局已经结束。')
            return
        self._confirm_manual_end(lambda: None)

    def _on_toggle_sound(self, *_args):
        self.sound_manager.enabled = not self.sound_manager.enabled
        if self.sound_manager.enabled:
            self.sound_btn.text = '音效:开'
            self.sound_btn.background_color = (0.22, 0.62, 0.24, 1)
            self.sound_manager.play('move')
        else:
            self.sound_btn.text = '音效:关'
            self.sound_btn.background_color = (0.58, 0.24, 0.24, 1)

    def _remember_window_size(self, *_args):
        try:
            self.account_store.save_window_size(self.username, int(Window.size[0]), int(Window.size[1]))
        except ValueError as exc:
            _show_popup('提示', str(exc))
            return
        _show_popup('成功', '已记住当前窗口大小，下次登录该账号时会自动恢复。')

    def _restore_default_window_size(self, *_args):
        self.account_store.clear_window_size(self.username)
        apply_desktop_window_setup(get_default_window_size())
        _show_popup('成功', '已恢复默认窗口大小，并清除该账号保存的尺寸记录。')

    def _on_logout(self, *_args):
        def do_logout():
            self._stop_timer()
            self.ai_pending = False
            self.manager.current = 'login'
            apply_desktop_window_setup(LOGIN_WINDOW_SIZE)
            login_screen = self.manager.get_screen('login')
            login_screen.refresh_usernames()
            login_screen.select_username(self.username)
            login_screen.password_input.text = ''

        if self._is_game_in_progress():
            self._confirm_manual_end(do_logout)
            return
        do_logout()

    def _get_move_sound(self, from_row, from_col, to_row, to_col, captured):
        gl = self.game_logic
        if captured:
            return 'capture'
        from_in_river = (from_row, from_col) in RIVER_CELLS
        to_in_river = (to_row, to_col) in RIVER_CELLS
        if not from_in_river and not to_in_river:
            if from_row == to_row:
                min_col = min(from_col, to_col)
                max_col = max(from_col, to_col)
                if any((from_row, col) in RIVER_CELLS for col in range(min_col + 1, max_col)):
                    return 'jump'
            elif from_col == to_col:
                min_row = min(from_row, to_row)
                max_row = max(from_row, to_row)
                if any((row, from_col) in RIVER_CELLS for row in range(min_row + 1, max_row)):
                    return 'jump'
        if to_in_river != from_in_river:
            return 'rat_water'
        moving_piece = gl.get_piece(to_row, to_col)
        if moving_piece:
            if moving_piece.color == 'red' and (to_row, to_col) in [(0, 2), (0, 4), (1, 3)]:
                return 'trap'
            if moving_piece.color == 'blue' and (to_row, to_col) in [(7, 3), (8, 2), (8, 4)]:
                return 'trap'
        return 'move'

    def _execute_move(self, from_row, from_col, to_row, to_col, is_ai=False):
        piece = self.game_logic.get_piece(from_row, from_col)
        if not piece:
            return
        result = self.game_logic.move_piece(from_row, from_col, to_row, to_col)
        if not result:
            return

        captured = self.game_logic.last_move_info and self.game_logic.last_move_info.get('captured')
        self.sound_manager.play(self._get_move_sound(from_row, from_col, to_row, to_col, captured))
        self.state_history.append(self.game_logic.to_dict())

        new_pieces = []
        for row in range(BOARD_ROWS):
            for col in range(BOARD_COLS):
                current_piece = self.game_logic.get_piece(row, col)
                if current_piece:
                    new_pieces.append((current_piece.row, current_piece.col, current_piece.color, current_piece.animal))

        self.board.selected_pos = []
        self.board.valid_moves = []

        capture_msg = None
        if captured:
            cap = self.game_logic.last_move_info['captured']
            if self.battle_mode == 'ai':
                who = 'AI' if is_ai else '你'
                target = '你' if is_ai else 'AI'
            else:
                who = '红方' if piece.color == 'red' else '蓝方'
                target = '蓝方' if piece.color == 'red' else '红方'
            capture_msg = f'{who}的{self.game_logic.last_move_info["piece"]}吃了{target}的{cap}。'

        self.step_label.text = f'第{len(self.state_history) - 1}步'

        self.board.start_move_animation(
            from_row,
            from_col,
            to_row,
            to_col,
            piece.color,
            piece.animal,
            new_pieces,
            on_done=lambda: self._on_move_anim_done(capture_msg, is_ai),
        )

    def _settlement_points(self):
        if self.battle_mode != 'ai':
            return 0
        return SCORE_BY_DIFFICULTY.get(self.current_difficulty, 0)

    def _praise_text(self):
        score = self._settlement_points()
        level = int(self.current_difficulty)
        if level >= 10:
            return '至尊级胜利！你已经压制了最强 AI，这一局堪称王者级表演。'
        if level >= 9:
            return '大师级胜利！你的判断、节奏和执行都非常强，这不是普通胜利。'
        if level >= 7:
            return '高难度胜利！这局赢得很硬，思路和稳定性都相当出色。'
        return f'胜利结算：本局获得 {score} 分。继续保持，你已经开始进入稳定强势状态。'

    def _encourage_text(self):
        return '这局暂时失利，但积分不会扣除。复盘关键几步，再来一局即可继续冲分。'

    def _finalize_game_result(self, feedback=True):
        if self.game_recorded:
            self._refresh_score_labels()
            return

        score = 0
        text = '本局 0 分'
        gl = self.game_logic
        difficulty_label = DIFFICULTY_PROFILES.get(self.current_difficulty, {}).get('label', '')

        if self.battle_mode == 'ai':
            if gl.winner == 'red':
                score = self._settlement_points()
                text = f'本局 +{score} 分'
            elif gl.draw_reason == 'manual_end':
                text = '本局 0 分（手动结束）'
            elif gl.draw_reason:
                text = f'本局 0 分（和棋：{self._draw_reason_label(gl.draw_reason)}）'
            else:
                text = '本局 0 分（挑战失败）'

            try:
                self.account_store.add_score_entry(
                    self.username,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    difficulty_label,
                    self.red_seconds,
                    self.blue_seconds,
                    score,
                )
            except Exception:
                pass
        else:
            text = '本局 0 分（双人模式不计分）'

        self.latest_game_score = score
        self.latest_game_score_text = text
        self.game_recorded = True
        self._refresh_score_labels()

        if feedback and self.battle_mode == 'ai':
            if gl.winner == 'red' and int(self.current_difficulty) >= 5:
                _show_popup('恭喜胜利', self._praise_text())
            elif gl.winner == 'blue':
                _show_popup('继续加油', self._encourage_text())

    def _on_move_anim_done(self, capture_msg, is_ai):
        self._update_turn_display()
        if capture_msg and not self.game_logic.game_over:
            self.status_label.text = capture_msg

        gl = self.game_logic
        if gl.game_over:
            self.ai_pending = False
            self._stop_timer()
            if gl.winner == 'red':
                self.sound_manager.play('win')
            elif gl.winner == 'blue':
                self.sound_manager.play('lose')
            elif gl.draw_reason:
                self.sound_manager.play('draw')
            self._finalize_game_result(feedback=True)
            return

        if self.battle_mode == 'ai' and gl.current_turn == 'blue' and not is_ai:
            self._trigger_ai_move()
        elif gl.current_turn == 'red' and is_ai:
            self.status_label.text = '请点击红方棋子'
            self.ai_pending = False

    def _on_undo(self, *_args):
        gl = self.game_logic
        if gl.game_over and self.game_recorded:
            _show_popup('提示', '对局已结算，无法悔棋。')
            return
        if self.board.is_animating():
            self.status_label.text = '棋子移动中，不能悔棋'
            return
        if self.ai_pending:
            self.status_label.text = 'AI 思考中，不能悔棋'
            return
        if len(self.state_history) <= 1:
            _show_popup('提示', '当前没有可撤销的走法。')
            return

        steps = min(2, len(self.state_history) - 1) if self.battle_mode == 'ai' else 1
        for _ in range(steps):
            self.state_history.pop()

        self.game_logic = GameLogic.from_dict(self.state_history[-1])
        self.ai_pending = False
        self.game_recorded = False
        self.latest_game_score = None
        self.latest_game_score_text = ''
        self.board.selected_pos = []
        self.board.valid_moves = []
        self.board.last_move_from = []
        self.board.last_move_to = []
        self._sync_pieces()
        self._update_turn_display()
        self._refresh_score_labels()
        self._update_time_labels()
        self.status_label.text = '已悔棋，可重新选择走法'

    def _on_save(self, *_args):
        default_dir = self._get_default_save_dir()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_name = f'{self.username}_{timestamp}.json'
        if not supports_native_file_dialogs():
            self._show_save_game_popup(default_dir, default_name)
            return
        try:
            filepath = choose_save_path(default_name, default_dir)
        except Exception as exc:
            _show_popup('保存失败', f'无法打开保存对话框：{exc}')
            return
        if not filepath:
            return

        self._save_to_path(filepath)

    def _show_save_game_popup(self, save_dir, suggested_name):
        popup = SaveGamePopup(
            save_dir=save_dir,
            suggested_name=suggested_name,
            on_confirm=lambda filename: self._save_to_path(choose_save_path(filename, save_dir)),
        )
        popup.open()

    def _save_to_path(self, filepath):
        if not filepath:
            return

        payload = {
            'username': self.username,
            'difficulty': self.current_difficulty,
            'battle_mode': self.battle_mode,
            'sound_enabled': self.sound_manager.enabled,
            'game_state': self.game_logic.to_dict(),
            'red_seconds': self.red_seconds,
            'blue_seconds': self.blue_seconds,
            'state_history': self.state_history,
            'game_recorded': self.game_recorded,
            'latest_game_score': self.latest_game_score,
            'latest_game_score_text': self.latest_game_score_text,
            'saved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

        try:
            with open(filepath, 'w', encoding='utf-8') as file:
                json.dump(payload, file, ensure_ascii=False, indent=2)
        except OSError as exc:
            _show_popup('保存失败', f'无法保存文件：{exc}')
            return
        _show_popup('保存成功', f'对局已保存到：\n{os.path.basename(filepath)}')

    def _on_load(self, *_args):
        default_dir = self._get_default_save_dir()
        if not supports_native_file_dialogs():
            self._show_saved_games_popup(default_dir)
            return
        try:
            filepath = choose_load_path(default_dir)
        except Exception as exc:
            _show_popup('读取失败', f'无法打开读取对话框：{exc}')
            return
        if not filepath:
            return

        self._load_from_path(filepath)

    def _show_saved_games_popup(self, save_dir):
        popup = SavedGamesPopup(save_dir=save_dir, on_select=self._load_from_path)
        popup.open()

    def _load_from_path(self, filepath):
        if not filepath:
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError) as exc:
            _show_popup('读取失败', f'无法读取文件：{exc}')
            return

        try:
            self.game_logic = GameLogic.from_dict(payload['game_state'])
        except Exception as exc:
            _show_popup('读取失败', f'存档格式不正确：{exc}')
            return

        self.current_difficulty = payload.get('difficulty', '5')
        self.battle_mode = payload.get('battle_mode', 'ai')
        self.red_seconds = max(0, int(payload.get('red_seconds', 0)))
        self.blue_seconds = max(0, int(payload.get('blue_seconds', 0)))
        self.state_history = payload.get('state_history', [self.game_logic.to_dict()])
        self.game_recorded = bool(payload.get('game_recorded', False))
        self.latest_game_score = payload.get('latest_game_score')
        self.latest_game_score_text = str(payload.get('latest_game_score_text', ''))
        self.ai_pending = False
        self.ai_player = AIPlayer(color='blue', difficulty=self.current_difficulty)

        self._suppress_spinner_callback = True
        self.mode_spinner.text = '人机对战' if self.battle_mode == 'ai' else '双人对战'
        self.difficulty_spinner.text = DIFFICULTY_PROFILES.get(self.current_difficulty, DIFFICULTY_PROFILES['5'])['label']
        self._suppress_spinner_callback = False

        self.sound_manager.enabled = bool(payload.get('sound_enabled', True))
        if self.sound_manager.enabled:
            self.sound_btn.text = '音效:开'
            self.sound_btn.background_color = (0.22, 0.62, 0.24, 1)
        else:
            self.sound_btn.text = '音效:关'
            self.sound_btn.background_color = (0.58, 0.24, 0.24, 1)

        self.board.selected_pos = []
        self.board.valid_moves = []
        self.board.last_move_from = []
        self.board.last_move_to = []
        self._sync_pieces()
        self._update_turn_display()
        self._refresh_score_labels()
        self._update_time_labels()
        self.status_label.text = '存档已读取'
        if not self.game_logic.game_over:
            self._start_timer()

        if not self.game_logic.game_over and self.game_logic.current_turn == 'blue' and self.battle_mode == 'ai':
            self._trigger_ai_move()

        _show_popup('读取成功', f'存档已加载：\n{os.path.basename(filepath)}')

    def _on_cell_click(self, row, col):
        gl = self.game_logic
        if gl.game_over or self.board.is_animating() or self.ai_pending:
            if gl.game_over:
                self.status_label.text = '游戏已结束，可开始新对局。'
            return

        if self.battle_mode == 'ai' and gl.current_turn == 'blue':
            self.status_label.text = 'AI 思考中，请稍候...'
            return

        clicked_piece = gl.get_piece(row, col)
        current_color = gl.current_turn

        if self.board.selected_pos:
            sel_row, sel_col = self.board.selected_pos
            if row == sel_row and col == sel_col:
                self.board.selected_pos = []
                self.board.valid_moves = []
                self._update_turn_display()
                return
            if clicked_piece and clicked_piece.color == current_color:
                self._select_piece(row, col)
                return
            if gl.is_valid_move(sel_row, sel_col, row, col):
                self._execute_move(sel_row, sel_col, row, col, is_ai=False)
                return
            self.status_label.text = '走棋无效，请重新选择'
            self.board.selected_pos = []
            self.board.valid_moves = []
            return

        if clicked_piece and clicked_piece.color == current_color:
            self._select_piece(row, col)
        else:
            color_name = '红方' if current_color == 'red' else '蓝方'
            self.status_label.text = f'请选择{color_name}棋子'

    def _select_piece(self, row, col):
        piece = self.game_logic.get_piece(row, col)
        if not piece:
            return
        self.board.selected_pos = [row, col]
        self.board.valid_moves = self.game_logic.get_valid_moves(row, col)
        owner = '你的' if self.battle_mode == 'ai' and piece.color == 'red' else ('红方' if piece.color == 'red' else '蓝方')
        self.status_label.text = f'选中{owner}{piece.animal}，请点击目标格'

    def _trigger_ai_move(self):
        self.ai_pending = True
        Clock.schedule_once(self._ai_do_move, 0.5)

    def _ai_do_move(self, _dt):
        if self.game_logic.game_over or self.game_logic.current_turn != 'blue':
            self.ai_pending = False
            return
        move = self.ai_player.get_best_move(self.game_logic)
        if move:
            (from_row, from_col), (to_row, to_col) = move
            self._execute_move(from_row, from_col, to_row, to_col, is_ai=True)
            return
        self.status_label.text = 'AI 无合法走法，游戏结束'
        self.game_logic.game_over = True
        self.game_logic.winner = 'red'
        self._update_turn_display()
        self.ai_pending = False
        self._stop_timer()
        self._finalize_game_result(feedback=True)


class JungleChessApp(App):
    title = '斗兽棋'

    def build(self):
        Window.clearcolor = (0.10, 0.14, 0.20, 1)
        apply_desktop_window_setup(LOGIN_WINDOW_SIZE)
        configure_soft_input_mode()
        Window.bind(on_keyboard=self._on_window_keyboard)
        Window.bind(size=self._on_window_size_changed)

        icon_path = get_desktop_icon_path()
        if icon_path and os.path.exists(icon_path):
            self.icon = icon_path

        self.account_store = AccountStore()

        self.sm = ScreenManager()
        self.sm.add_widget(LoginScreen(self.account_store, on_login_success=self._on_login_success, name='login'))
        self.sm.add_widget(RegisterScreen(self.account_store, name='register'))
        self.sm.add_widget(ChangePasswordScreen(self.account_store, name='change_password'))
        self.sm.add_widget(ResetPasswordScreen(self.account_store, name='reset_password'))
        return self.sm

    def _dismiss_top_modal(self):
        for child in list(reversed(Window.children)):
            if isinstance(child, ModalView):
                child.dismiss()
                return True
        return False

    def _show_exit_app_popup(self):
        content = BoxLayout(orientation='vertical', spacing=10, padding=12)
        text = _mk_label(
            '确认退出斗兽棋？',
            font_size='14sp',
            color=(0.94, 0.94, 0.94, 1),
            size_hint_y=None,
            height=50,
        )
        buttons = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
        cancel_btn = _mk_button('取消', background_color=(0.40, 0.30, 0.30, 1))
        exit_btn = _mk_button('退出', background_color=(0.56, 0.28, 0.22, 1))
        buttons.add_widget(cancel_btn)
        buttons.add_widget(exit_btn)
        content.add_widget(text)
        content.add_widget(buttons)

        popup = Popup(
            title='退出程序',
            content=content,
            size_hint=(0.46, 0.28),
            background_color=(0.14, 0.15, 0.22, 0.98),
            title_color=(1, 1, 1, 1),
        )
        if CHINESE_FONT:
            popup.title_font = CHINESE_FONT

        cancel_btn.bind(on_press=lambda *_: popup.dismiss())
        exit_btn.bind(on_press=lambda *_: (popup.dismiss(), Clock.schedule_once(lambda _dt: self.stop(), 0)))
        popup.open()

    def _handle_android_back(self):
        if self._dismiss_top_modal():
            return True

        current = self.sm.current if getattr(self, 'sm', None) else ''
        if current in {'register', 'change_password', 'reset_password'}:
            self.sm.current = 'login'
            return True

        if current == 'game' and self.sm.has_screen('game'):
            self.sm.get_screen('game')._on_logout()
            return True

        if current == 'login':
            self._show_exit_app_popup()
            return True

        return False

    def _on_window_keyboard(self, _window, key, _scancode, _codepoint, _modifiers):
        if key != 27 or not is_android():
            return False
        return self._handle_android_back()

    def on_stop(self):
        Window.unbind(on_keyboard=self._on_window_keyboard)
        try:
            Window.unbind(size=self._on_window_size_changed)
        except Exception:
            pass

    def _on_window_size_changed(self, *_args):
        if is_android():
            return
        Clock.schedule_once(lambda _dt: center_window(Window.size), 0)

    def _on_login_success(self, username):
        saved_size = self.account_store.get_window_size(username)
        apply_desktop_window_setup(saved_size or get_default_window_size())

        if self.sm.has_screen('game'):
            self.sm.remove_widget(self.sm.get_screen('game'))

        game_screen = GameScreen(username=username, account_store=self.account_store, name='game')
        self.sm.add_widget(game_screen)
        self.sm.current = 'game'


if __name__ == '__main__':
    JungleChessApp().run()
