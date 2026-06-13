"""
auth_screen.py - Kivy 版账号登录/注册界面
用 Kivy Screen 实现原版 PyQt5 的 LoginDialog / RegisterDialog / ChangePasswordDialog / ResetPasswordDialog
布局优化：充分利用宽度方向，减少高度占用
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core'))

from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.properties import ObjectProperty, StringProperty
from kivy.app import App
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, Line, RoundedRectangle
from kivy.clock import Clock

try:
    from .auth_logic import AccountStore, MASTER_PASSWORD
except ImportError:
    from auth_logic import AccountStore, MASTER_PASSWORD

try:
    from .board_widget import hex_to_rgb, CHINESE_FONT, KV_COLORS
except ImportError:
    from board_widget import hex_to_rgb, CHINESE_FONT, KV_COLORS
from platform_services.device import get_viewport_metrics, scaled


# ─── 通用工具 ─────────────────────────────────────────────

def _mk_label(text, font_size='18sp', color=(1,1,1,1), **kwargs):
    lbl = Label(text=text, font_size=font_size, color=color, **kwargs)
    if CHINESE_FONT:
        lbl.font_name = CHINESE_FONT
    return lbl


def _mix_color(color_a, color_b, amount):
    amount = max(0.0, min(1.0, float(amount)))
    return tuple(color_a[i] * (1.0 - amount) + color_b[i] * amount for i in range(4))


def _darken(color, amount):
    return _mix_color(color, (0.0, 0.0, 0.0, color[3]), amount)


def _lighten(color, amount):
    return _mix_color(color, (1.0, 1.0, 1.0, color[3]), amount)


def _mk_button(text, font_size='14sp', **kwargs):
    background_color = tuple(kwargs.get('background_color', (0.22, 0.48, 0.72, 1)))
    kwargs.setdefault('background_normal', '')
    kwargs.setdefault('background_down', '')
    btn = Button(text=text, font_size=font_size, **kwargs)
    if CHINESE_FONT:
        btn.font_name = CHINESE_FONT
    btn.background_color = background_color

    radius = 8
    with btn.canvas.before:
        shadow_color = Color(*_darken(background_color, 0.34))
        shadow = RoundedRectangle(pos=(btn.x, btn.y - 2), size=(btn.width, btn.height), radius=[radius])
        body_color = Color(*background_color)
        body = RoundedRectangle(pos=(btn.x, btn.y), size=(btn.width, btn.height), radius=[radius])
        highlight_color = Color(*_lighten(background_color, 0.10))
        highlight = RoundedRectangle(
            pos=(btn.x, btn.y + btn.height * 0.52),
            size=(btn.width, btn.height * 0.46),
            radius=[radius, radius, max(1, radius - 2), max(1, radius - 2)],
        )
        sheen_color = Color(1, 1, 1, 0.10)
        sheen = RoundedRectangle(
            pos=(btn.x, btn.y + btn.height * 0.66),
            size=(btn.width, btn.height * 0.16),
            radius=[radius, radius, 0, 0],
        )
        border_color = Color(0, 0, 0, 0.28)
        border = Line(rounded_rectangle=(btn.x, btn.y, btn.width, btn.height, radius), width=1.1)

    def _sync(*_args):
        is_down = btn.state == 'down'
        current = tuple(btn.background_color)
        shadow.pos = (btn.x, btn.y - (1 if not is_down else 0))
        shadow.size = (btn.width, btn.height)
        body.pos = (btn.x, btn.y + (1 if not is_down else 0))
        body.size = (btn.width, max(1, btn.height - (1 if not is_down else 0)))
        highlight.pos = (btn.x, btn.y + btn.height * 0.52)
        highlight.size = (btn.width, btn.height * 0.46)
        sheen.pos = (btn.x, btn.y + btn.height * 0.66)
        sheen.size = (btn.width, btn.height * 0.16)
        shadow_color.rgba = _darken(current, 0.48 if is_down else 0.34)
        body_color.rgba = _darken(current, 0.08 if is_down else 0.00)
        highlight_color.rgba = _lighten(current, 0.03 if is_down else 0.10)
        sheen_color.rgba = (1, 1, 1, 0.05 if is_down else 0.10)
        border_color.rgba = _darken(current, 0.60 if is_down else 0.42)
        border.rounded_rectangle = (btn.x, btn.y, btn.width, btn.height, radius)

    btn.bind(pos=_sync, size=_sync, state=_sync, background_color=_sync)
    _sync()
    return btn


def _mk_input(hint='', password=False, font_size='16sp', **kwargs):
    """创建带中文字体的输入框"""
    ti = TextInput(
        hint_text=hint,
        password=password,
        font_size=font_size,
        multiline=False,
        size_hint_y=None,
        height=40,
        **kwargs,
    )
    if CHINESE_FONT:
        ti.font_name = CHINESE_FONT
    return ti


def _show_popup(title, message):
    """弹出一个简单的提示框"""
    content = BoxLayout(orientation='vertical', padding=10, spacing=10)
    msg_label = _mk_label(message, font_size='16sp', size_hint_y=0.7)
    close_btn = _mk_button('确定', size_hint_y=0.3,
                           background_color=(0.2, 0.5, 0.8, 1))
    content.add_widget(msg_label)
    content.add_widget(close_btn)

    popup = Popup(
        title=title,
        content=content,
        size_hint=(0.6, 0.35),
        background_color=(0.15, 0.22, 0.35, 0.95),
        title_color=(1, 1, 1, 1),
    )
    if CHINESE_FONT:
        popup.title_font = CHINESE_FONT
    close_btn.bind(on_press=popup.dismiss)
    popup.open()
    return popup


def _set_block_background(widget, bg_color=(0.12, 0.18, 0.28, 0.92),
                          border_color=(0.30, 0.40, 0.52, 1.0)):
    """给布局容器添加简洁的背景和边框。"""
    with widget.canvas.before:
        Color(*bg_color)
        bg = Rectangle(pos=widget.pos, size=widget.size)
        Color(*border_color)
        border = Line(rectangle=(widget.x, widget.y, widget.width, widget.height), width=1.2)

    def _update_rect(*_args):
        bg.pos = widget.pos
        bg.size = widget.size
        border.rectangle = (widget.x, widget.y, widget.width, widget.height)

    widget.bind(pos=_update_rect, size=_update_rect)


def _enable_label_wrap(label, halign='left', valign='middle'):
    """让 Label 按宽度自动换行。"""
    label.halign = halign
    label.valign = valign

    def _sync_text_size(instance, value):
        instance.text_size = (value[0], None)

    label.bind(size=_sync_text_size)
    return label


def _make_scroll_form(padding=30, spacing=8):
    scroll = ScrollView(do_scroll_x=False, do_scroll_y=True, bar_width=10, scroll_type=['bars', 'content'])
    layout = BoxLayout(orientation='vertical', padding=padding, spacing=spacing, size_hint_y=None)
    layout.bind(minimum_height=layout.setter('height'))
    scroll.add_widget(layout)
    return scroll, layout


def _bind_scroll_focus(scroll, *widgets):
    for widget in widgets:
        def _on_focus(instance, focused, target=widget):
            if focused:
                Clock.schedule_once(lambda _dt: scroll.scroll_to(target, padding=24, animate=False), 0.05)

        widget.bind(focus=_on_focus)


# ─── 登录界面 ─────────────────────────────────────────────

class LoginScreen(Screen):
    """登录界面 — 居中卡片布局"""

    def __init__(self, account_store, on_login_success, **kwargs):
        super().__init__(**kwargs)
        self.store = account_store
        self.on_login_success = on_login_success

        self.login_scroll = ScrollView(do_scroll_x=False, do_scroll_y=True, bar_width=10, scroll_type=['bars', 'content'])
        self.outer = BoxLayout(orientation='vertical', padding=[18, 14, 18, 14], size_hint_y=None)
        self.outer.add_widget(BoxLayout())

        self.middle_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=392)
        self.middle_row.add_widget(BoxLayout())

        self.login_card = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            width=470,
            height=388,
            padding=[24, 20, 24, 20],
            spacing=14,
        )
        _set_block_background(
            self.login_card,
            bg_color=(0.11, 0.17, 0.25, 0.90),
            border_color=(0.29, 0.39, 0.50, 0.62),
        )

        self.header = BoxLayout(orientation='vertical', size_hint_y=None, height=124, spacing=4)
        title = _mk_label(
            '斗兽棋', font_size='32sp',
            color=hex_to_rgb('#FFD700'),
            size_hint_y=None, height=46,
        )
        subtitle = _mk_label(
            'Kivy 跨平台版', font_size='14sp',
            color=(0.74, 0.82, 0.92, 1),
            size_hint_y=None, height=22,
        )
        deco = _mk_label(
            '象 狮 虎 豹 狼 狗 猫 鼠', font_size='15sp',
            color=hex_to_rgb('#D7B96B'),
            size_hint_y=None, height=20,
        )
        self.tip_label = _enable_label_wrap(_mk_label(
            '', font_size='11sp',
            color=(0.83, 0.83, 0.68, 1),
            size_hint_y=None, height=24,
        ), halign='center')
        self.header.add_widget(title)
        self.header.add_widget(subtitle)
        self.header.add_widget(deco)
        self.header.add_widget(self.tip_label)

        form_title = _mk_label(
            '账号登录', font_size='18sp',
            color=(0.95, 0.95, 0.95, 1),
            size_hint_y=None, height=24,
        )

        user_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=38, spacing=10)
        user_label = _mk_label(
            '用户名', font_size='14sp',
            color=(0.72, 0.82, 0.92, 1),
            size_hint_x=0.22,
        )
        username_field = BoxLayout(orientation='horizontal', size_hint_x=0.78, spacing=6)
        self.username_input = _mk_input(hint='请输入用户名', size_hint_x=1.0)
        self.user_dropdown = DropDown(auto_width=False, width=260)
        self.user_dropdown.bind(on_select=self._on_user_selected)
        self.user_menu_btn = _mk_button(
            '▼',
            font_size='13sp',
            size_hint_x=None,
            width=44,
            background_color=(0.22, 0.34, 0.46, 1),
        )
        self.user_menu_btn.bind(on_press=self._open_user_dropdown)
        username_field.add_widget(self.username_input)
        username_field.add_widget(self.user_menu_btn)
        user_row.add_widget(user_label)
        user_row.add_widget(username_field)

        pass_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=38, spacing=10)
        pass_label = _mk_label(
            '密码', font_size='14sp',
            color=(0.72, 0.82, 0.92, 1),
            size_hint_x=0.22,
        )
        self.password_input = _mk_input(hint='请输入密码', password=True, size_hint_x=0.78)
        self.password_input.bind(on_text_validate=self._on_login)
        pass_row.add_widget(pass_label)
        pass_row.add_widget(self.password_input)

        main_btns = BoxLayout(orientation='horizontal', size_hint_y=None, height=42, spacing=10)
        login_btn = _mk_button(
            '登 录', font_size='17sp',
            background_color=(0.15, 0.55, 0.85, 1),
        )
        login_btn.bind(on_press=self._on_login)
        register_btn = _mk_button(
            '注册新账号', font_size='14sp',
            background_color=(0.2, 0.5, 0.3, 1),
        )
        register_btn.bind(on_press=self._on_goto_register)
        main_btns.add_widget(login_btn)
        main_btns.add_widget(register_btn)

        minor_btns = GridLayout(cols=3, size_hint_y=None, height=36, spacing=8)
        change_pwd_btn = _mk_button(
            '修改密码', font_size='12sp',
            background_color=(0.4, 0.35, 0.25, 1),
        )
        change_pwd_btn.bind(on_press=self._on_goto_change_pwd)
        reset_pwd_btn = _mk_button(
            '找回密码', font_size='12sp',
            background_color=(0.4, 0.35, 0.25, 1),
        )
        reset_pwd_btn.bind(on_press=self._on_goto_reset_pwd)
        quit_btn = _mk_button(
            '退出', font_size='12sp',
            background_color=(0.5, 0.2, 0.2, 1),
        )
        quit_btn.bind(on_press=self._on_quit)
        minor_btns.add_widget(change_pwd_btn)
        minor_btns.add_widget(reset_pwd_btn)
        minor_btns.add_widget(quit_btn)

        self.login_card.add_widget(self.header)
        self.login_card.add_widget(form_title)
        self.login_card.add_widget(user_row)
        self.login_card.add_widget(pass_row)
        self.login_card.add_widget(main_btns)
        self.login_card.add_widget(minor_btns)

        self.middle_row.add_widget(self.login_card)
        self.middle_row.add_widget(BoxLayout())

        self.outer.add_widget(self.middle_row)
        self.outer.add_widget(BoxLayout())
        self.login_scroll.add_widget(self.outer)
        self.add_widget(self.login_scroll)
        _bind_scroll_focus(self.login_scroll, self.username_input, self.password_input)
        self.bind(size=self._update_login_layout)
        self._update_login_layout()

        # 填入上次的用户名
        self.refresh_usernames()
        last_user = self.store.get_last_username()
        if last_user:
            self.select_username(last_user)
        self._update_tip()

    def _update_tip(self):
        if self.store.has_users():
            self.tip_label.text = '已登录过的用户名会被记住'
        else:
            self.tip_label.text = '首次使用请先注册账号'

    def _update_login_layout(self, *_args):
        if not hasattr(self, 'login_card'):
            return

        metrics = get_viewport_metrics((self.width, self.height))
        is_portrait = not metrics.is_landscape
        outer_pad_x = scaled(18 if is_portrait else 22, metrics, min_value=10, max_value=28)
        outer_pad_y = scaled(14 if is_portrait else 18, metrics, min_value=8, max_value=22)
        self.outer.padding = [outer_pad_x, outer_pad_y, outer_pad_x, outer_pad_y]
        card_target_width = 360 if is_portrait else 470
        card_max_width = 420 if is_portrait else 560
        self.middle_row.height = scaled(416 if is_portrait else 408, metrics, min_value=386, max_value=520)
        self.outer.height = max(self.height, self.middle_row.height + outer_pad_y * 2 + 24)
        self.login_card.width = min(
            scaled(card_target_width, metrics, min_value=320, max_value=card_max_width),
            max(300, int(self.width - outer_pad_x * 2 - (10 if is_portrait else 16))),
        )
        self.login_card.height = scaled(388 if is_portrait else 384, metrics, min_value=372, max_value=476)
        self.login_card.padding = [
            scaled(22 if is_portrait else 24, metrics, min_value=16, max_value=32),
            scaled(18 if is_portrait else 20, metrics, min_value=14, max_value=26),
            scaled(22 if is_portrait else 24, metrics, min_value=16, max_value=32),
            scaled(18 if is_portrait else 20, metrics, min_value=14, max_value=26),
        ]
        self.login_card.spacing = scaled(12 if is_portrait else 14, metrics, min_value=10, max_value=18)
        self.header.height = scaled(112 if is_portrait else 118, metrics, min_value=102, max_value=140)
        self.header.spacing = scaled(4, metrics, min_value=3, max_value=8)

    def refresh_usernames(self):
        self.user_dropdown.clear_widgets()
        usernames = self.store.get_usernames()
        self.user_menu_btn.disabled = not bool(usernames)
        for username in usernames:
            item = _mk_button(
                username,
                size_hint_y=None,
                height=40,
                background_color=(0.16, 0.24, 0.34, 1),
            )
            item.bind(on_release=lambda btn: self.user_dropdown.select(btn.text))
            self.user_dropdown.add_widget(item)

    def _open_user_dropdown(self, button):
        self.refresh_usernames()
        if not self.user_menu_btn.disabled:
            self.user_dropdown.open(button)

    def _on_user_selected(self, dropdown, username):
        self.select_username(username)

    def select_username(self, username):
        self.username_input.text = username
        self.password_input.focus = True

    def _on_login(self, *args):
        username = self.username_input.text.strip()
        password = self.password_input.text

        if not username:
            _show_popup('提示', '请输入用户名')
            return
        if not password:
            _show_popup('提示', '请输入密码')
            return
        if not self.store.verify_login(username, password):
            _show_popup('登录失败', '用户名或密码不正确')
            return

        try:
            self.store.remember_username(username)
        except OSError as exc:
            _show_popup('提示', f'保存登录信息失败：{exc}')
            return

        if self.on_login_success:
            self.on_login_success(username)

    def _on_goto_register(self, *args):
        self.manager.current = 'register'

    def _on_goto_change_pwd(self, *args):
        if not self.store.has_users():
            _show_popup('提示', '当前没有账号，请先注册')
            return
        self.manager.current = 'change_password'

    def _on_goto_reset_pwd(self, *args):
        if not self.store.has_users():
            _show_popup('提示', '当前没有账号，请先注册')
            return
        self.manager.current = 'reset_password'

    def _on_quit(self, *args):
        app = App.get_running_app()
        if app:
            app.stop()
        else:
            Window.close()


# ─── 注册界面 ─────────────────────────────────────────────

class RegisterScreen(Screen):
    """注册界面"""

    def __init__(self, account_store, **kwargs):
        super().__init__(**kwargs)
        self.store = account_store

        root, layout = _make_scroll_form(padding=30, spacing=8)

        title = _mk_label('注册新账号', font_size='24sp',
                          color=hex_to_rgb('#FFD700'), size_hint_y=0.10)
        tip = _mk_label('首次使用请先注册账号', font_size='14sp',
                       color=(0.7, 0.8, 0.9, 1), size_hint_y=0.06)

        # 用户名行
        user_row = BoxLayout(orientation='horizontal', size_hint_y=None,
                            height=36, spacing=8)
        user_label = _mk_label('用户名', font_size='14sp',
                              color=(0.7, 0.8, 0.9, 1), size_hint_x=0.30)
        self.username_input = _mk_input(hint='请输入用户名', size_hint_x=0.70)
        user_row.add_widget(user_label)
        user_row.add_widget(self.username_input)

        # 密码行
        pass_row = BoxLayout(orientation='horizontal', size_hint_y=None,
                            height=36, spacing=8)
        pass_label = _mk_label('密码', font_size='14sp',
                              color=(0.7, 0.8, 0.9, 1), size_hint_x=0.30)
        self.password_input = _mk_input(hint='请输入密码', password=True, size_hint_x=0.70)
        pass_row.add_widget(pass_label)
        pass_row.add_widget(self.password_input)

        # 确认密码行
        confirm_row = BoxLayout(orientation='horizontal', size_hint_y=None,
                               height=36, spacing=8)
        confirm_label = _mk_label('确认密码', font_size='14sp',
                                 color=(0.7, 0.8, 0.9, 1), size_hint_x=0.30)
        self.confirm_input = _mk_input(hint='请再次输入密码', password=True, size_hint_x=0.70)
        self.confirm_input.bind(on_text_validate=self._on_register)
        confirm_row.add_widget(confirm_label)
        confirm_row.add_widget(self.confirm_input)

        # 按钮
        btn_area = BoxLayout(orientation='horizontal', spacing=15,
                            size_hint_y=None, height=42, padding=(0, 5))
        register_btn = _mk_button('注 册', font_size='18sp',
                                 background_color=(0.15, 0.55, 0.85, 1))
        register_btn.bind(on_press=self._on_register)
        cancel_btn = _mk_button('取消', font_size='16sp',
                               background_color=(0.4, 0.3, 0.3, 1))
        cancel_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'login'))
        btn_area.add_widget(register_btn)
        btn_area.add_widget(cancel_btn)

        layout.add_widget(title)
        layout.add_widget(tip)
        layout.add_widget(user_row)
        layout.add_widget(pass_row)
        layout.add_widget(confirm_row)
        layout.add_widget(btn_area)

        _bind_scroll_focus(
            root,
            self.username_input,
            self.password_input,
            self.confirm_input,
        )
        self.add_widget(root)

    def _on_register(self, *args):
        username = self.username_input.text.strip()
        password = self.password_input.text
        confirm = self.confirm_input.text

        if password != confirm:
            _show_popup('提示', '两次输入的密码不一致')
            return

        try:
            self.store.register_user(username, password)
        except ValueError as exc:
            _show_popup('注册失败', str(exc))
            return
        except OSError as exc:
            _show_popup('注册失败', f'保存账号失败：{exc}')
            return

        _show_popup('注册成功', '注册完成，请使用新账号登录')
        login_screen = self.manager.get_screen('login')
        login_screen.refresh_usernames()
        login_screen.select_username(username)
        login_screen.password_input.text = ''
        login_screen._update_tip()
        self.manager.current = 'login'

        self.username_input.text = ''
        self.password_input.text = ''
        self.confirm_input.text = ''


# ─── 修改密码界面 ─────────────────────────────────────────

class ChangePasswordScreen(Screen):
    """修改密码界面"""

    def __init__(self, account_store, **kwargs):
        super().__init__(**kwargs)
        self.store = account_store

        root, layout = _make_scroll_form(padding=30, spacing=8)

        title = _mk_label('修改密码', font_size='24sp',
                          color=hex_to_rgb('#FFD700'), size_hint_y=0.10)

        # 用户名行
        user_row = BoxLayout(orientation='horizontal', size_hint_y=None,
                            height=36, spacing=8)
        user_label = _mk_label('用户名', font_size='14sp',
                              color=(0.7, 0.8, 0.9, 1), size_hint_x=0.30)
        self.username_input = _mk_input(hint='请输入用户名', size_hint_x=0.70)
        user_row.add_widget(user_label)
        user_row.add_widget(self.username_input)

        # 旧密码行
        old_row = BoxLayout(orientation='horizontal', size_hint_y=None,
                           height=36, spacing=8)
        old_label = _mk_label('旧密码', font_size='14sp',
                             color=(0.7, 0.8, 0.9, 1), size_hint_x=0.30)
        self.old_password_input = _mk_input(hint='请输入旧密码', password=True, size_hint_x=0.70)
        old_row.add_widget(old_label)
        old_row.add_widget(self.old_password_input)

        # 新密码行
        new_row = BoxLayout(orientation='horizontal', size_hint_y=None,
                           height=36, spacing=8)
        new_label = _mk_label('新密码', font_size='14sp',
                             color=(0.7, 0.8, 0.9, 1), size_hint_x=0.30)
        self.new_password_input = _mk_input(hint='请输入新密码', password=True, size_hint_x=0.70)
        new_row.add_widget(new_label)
        new_row.add_widget(self.new_password_input)

        # 确认新密码行
        confirm_row = BoxLayout(orientation='horizontal', size_hint_y=None,
                               height=36, spacing=8)
        confirm_label = _mk_label('确认新密码', font_size='14sp',
                                 color=(0.7, 0.8, 0.9, 1), size_hint_x=0.30)
        self.confirm_input = _mk_input(hint='请再次输入新密码', password=True, size_hint_x=0.70)
        self.confirm_input.bind(on_text_validate=self._on_submit)
        confirm_row.add_widget(confirm_label)
        confirm_row.add_widget(self.confirm_input)

        btn_area = BoxLayout(orientation='horizontal', spacing=15,
                            size_hint_y=None, height=42, padding=(0, 5))
        submit_btn = _mk_button('确认修改', font_size='16sp',
                               background_color=(0.15, 0.55, 0.85, 1))
        submit_btn.bind(on_press=self._on_submit)
        cancel_btn = _mk_button('取消', font_size='16sp',
                               background_color=(0.4, 0.3, 0.3, 1))
        cancel_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'login'))
        btn_area.add_widget(submit_btn)
        btn_area.add_widget(cancel_btn)

        layout.add_widget(title)
        layout.add_widget(user_row)
        layout.add_widget(old_row)
        layout.add_widget(new_row)
        layout.add_widget(confirm_row)
        layout.add_widget(btn_area)

        _bind_scroll_focus(
            root,
            self.username_input,
            self.old_password_input,
            self.new_password_input,
            self.confirm_input,
        )
        self.add_widget(root)

    def on_enter(self, *args):
        last = self.store.get_last_username()
        if last:
            self.username_input.text = last
        self.old_password_input.text = ''
        self.new_password_input.text = ''
        self.confirm_input.text = ''

    def _on_submit(self, *args):
        username = self.username_input.text.strip()
        old_password = self.old_password_input.text
        new_password = self.new_password_input.text
        confirm = self.confirm_input.text

        if new_password != confirm:
            _show_popup('提示', '两次输入的新密码不一致')
            return

        try:
            self.store.change_password(username, old_password, new_password)
        except ValueError as exc:
            _show_popup('修改失败', str(exc))
            return
        except OSError as exc:
            _show_popup('修改失败', f'保存失败：{exc}')
            return

        _show_popup('修改成功', '密码已更新，请使用新密码登录')
        self.manager.current = 'login'


# ─── 找回密码界面 ─────────────────────────────────────────

class ResetPasswordScreen(Screen):
    """找回密码界面（使用超级密码重置）"""

    def __init__(self, account_store, **kwargs):
        super().__init__(**kwargs)
        self.store = account_store

        root, layout = _make_scroll_form(padding=30, spacing=8)

        title = _mk_label('找回密码', font_size='24sp',
                          color=hex_to_rgb('#FFD700'), size_hint_y=0.08)
        tip = _mk_label(f'忘记密码时可使用超级密码找回\n超级密码：{MASTER_PASSWORD}',
                       font_size='13sp', color=(0.9, 0.7, 0.3, 1), size_hint_y=0.06)

        # 用户名行
        user_row = BoxLayout(orientation='horizontal', size_hint_y=None,
                            height=36, spacing=8)
        user_label = _mk_label('用户名', font_size='14sp',
                              color=(0.7, 0.8, 0.9, 1), size_hint_x=0.30)
        self.username_input = _mk_input(hint='请输入用户名', size_hint_x=0.70)
        user_row.add_widget(user_label)
        user_row.add_widget(self.username_input)

        # 超级密码行
        master_row = BoxLayout(orientation='horizontal', size_hint_y=None,
                              height=36, spacing=8)
        master_label = _mk_label('超级密码', font_size='14sp',
                                color=(0.7, 0.8, 0.9, 1), size_hint_x=0.30)
        self.master_input = _mk_input(hint='请输入超级密码', password=True, size_hint_x=0.70)
        master_row.add_widget(master_label)
        master_row.add_widget(self.master_input)

        # 新密码行
        new_row = BoxLayout(orientation='horizontal', size_hint_y=None,
                           height=36, spacing=8)
        new_label = _mk_label('新密码', font_size='14sp',
                             color=(0.7, 0.8, 0.9, 1), size_hint_x=0.30)
        self.new_password_input = _mk_input(hint='请输入新密码', password=True, size_hint_x=0.70)
        new_row.add_widget(new_label)
        new_row.add_widget(self.new_password_input)

        # 确认新密码行
        confirm_row = BoxLayout(orientation='horizontal', size_hint_y=None,
                               height=36, spacing=8)
        confirm_label = _mk_label('确认新密码', font_size='14sp',
                                 color=(0.7, 0.8, 0.9, 1), size_hint_x=0.30)
        self.confirm_input = _mk_input(hint='请再次输入新密码', password=True, size_hint_x=0.70)
        self.confirm_input.bind(on_text_validate=self._on_submit)
        confirm_row.add_widget(confirm_label)
        confirm_row.add_widget(self.confirm_input)

        btn_area = BoxLayout(orientation='horizontal', spacing=15,
                            size_hint_y=None, height=42, padding=(0, 5))
        submit_btn = _mk_button('重置密码', font_size='16sp',
                               background_color=(0.15, 0.55, 0.85, 1))
        submit_btn.bind(on_press=self._on_submit)
        cancel_btn = _mk_button('取消', font_size='16sp',
                               background_color=(0.4, 0.3, 0.3, 1))
        cancel_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'login'))
        btn_area.add_widget(submit_btn)
        btn_area.add_widget(cancel_btn)

        layout.add_widget(title)
        layout.add_widget(tip)
        layout.add_widget(user_row)
        layout.add_widget(master_row)
        layout.add_widget(new_row)
        layout.add_widget(confirm_row)
        layout.add_widget(btn_area)

        _bind_scroll_focus(
            root,
            self.username_input,
            self.master_input,
            self.new_password_input,
            self.confirm_input,
        )
        self.add_widget(root)

    def on_enter(self, *args):
        last = self.store.get_last_username()
        if last:
            self.username_input.text = last
        self.master_input.text = ''
        self.new_password_input.text = ''
        self.confirm_input.text = ''

    def _on_submit(self, *args):
        username = self.username_input.text.strip()
        master_password = self.master_input.text
        new_password = self.new_password_input.text
        confirm = self.confirm_input.text

        if new_password != confirm:
            _show_popup('提示', '两次输入的新密码不一致')
            return

        try:
            self.store.reset_password_with_master(username, master_password, new_password)
        except ValueError as exc:
            _show_popup('重置失败', str(exc))
            return
        except OSError as exc:
            _show_popup('重置失败', f'保存失败：{exc}')
            return

        _show_popup('重置成功', '密码已重置，请使用新密码登录')
        self.manager.current = 'login'
