from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core'))

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

try:
    from .auth_logic import MASTER_PASSWORD
except ImportError:
    from auth_logic import MASTER_PASSWORD

try:
    from .board_widget import CHINESE_FONT, hex_to_rgb
except ImportError:
    from board_widget import CHINESE_FONT, hex_to_rgb

from platform_services.device import get_viewport_metrics, scaled


def _mk_label(text, font_size='18sp', color=(1, 1, 1, 1), **kwargs):
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
    content = BoxLayout(orientation='vertical', padding=10, spacing=10)
    msg_label = _mk_label(message, font_size='16sp', size_hint_y=0.7)
    close_btn = _mk_button('确定', size_hint_y=0.3, background_color=(0.2, 0.5, 0.8, 1))
    content.add_widget(msg_label)
    content.add_widget(close_btn)

    popup = Popup(
        title=title,
        content=content,
        size_hint=(0.72, 0.36),
        background_color=(0.15, 0.22, 0.35, 0.95),
        title_color=(1, 1, 1, 1),
    )
    if CHINESE_FONT:
        popup.title_font = CHINESE_FONT
    close_btn.bind(on_press=popup.dismiss)
    popup.open()
    return popup


def _set_block_background(widget, bg_color=(0.12, 0.18, 0.28, 0.92), border_color=(0.30, 0.40, 0.52, 1.0)):
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


def _enable_wrap(label, halign='left', valign='middle'):
    label.halign = halign
    label.valign = valign

    def _sync(instance, value):
        instance.text_size = (value[0], None)

    label.bind(size=_sync)
    return label


class _BaseFormScreen(Screen):
    title_text = ''
    tip_text = ''
    submit_text = ''
    cancel_text = '取消'

    def __init__(self, account_store, **kwargs):
        super().__init__(**kwargs)
        self.store = account_store
        self.scroll = ScrollView(do_scroll_x=False, do_scroll_y=True, bar_width=10, scroll_type=['bars', 'content'])
        self.outer = BoxLayout(orientation='vertical', size_hint_y=None, padding=[16, 16, 16, 16])
        self.outer.bind(minimum_height=self.outer.setter('height'))
        self.scroll.add_widget(self.outer)
        self.card = BoxLayout(orientation='vertical', size_hint=(None, None), spacing=12, padding=[18, 18, 18, 18])
        self.card.bind(minimum_height=self.card.setter('height'))
        _set_block_background(self.card, bg_color=(0.11, 0.17, 0.25, 0.90), border_color=(0.29, 0.39, 0.50, 0.62))
        self.top_spacer = BoxLayout(size_hint_y=1)
        self.bottom_spacer = BoxLayout(size_hint_y=1)
        self.outer.add_widget(self.top_spacer)
        self.outer.add_widget(self.card)
        self.outer.add_widget(self.bottom_spacer)
        self.add_widget(self.scroll)
        self.bind(size=self._update_layout)
        Clock.schedule_once(lambda *_: self._reset_scroll(), 0)

    def _reset_scroll(self):
        self.scroll.scroll_y = 1

    def _build_header(self):
        header = BoxLayout(orientation='vertical', size_hint_y=None, spacing=4, height=92)
        self.title_label = _mk_label(self.title_text, font_size='24sp', color=hex_to_rgb('#FFD700'), size_hint_y=None, height=38)
        self.tip_label = _enable_wrap(_mk_label(self.tip_text, font_size='13sp', color=(0.80, 0.82, 0.66, 1), size_hint_y=None, height=42), halign='center')
        header.add_widget(self.title_label)
        header.add_widget(self.tip_label)
        return header

    def _build_field_row(self, label_text, input_widget):
        row = BoxLayout(orientation='horizontal', size_hint_y=None, height=46, spacing=10)
        label = _mk_label(label_text, font_size='14sp', color=(0.72, 0.82, 0.92, 1), size_hint_x=0.28)
        row.add_widget(label)
        row.add_widget(input_widget)
        return row

    def _build_buttons(self):
        buttons = BoxLayout(orientation='horizontal', size_hint_y=None, height=46, spacing=10)
        submit_btn = _mk_button(self.submit_text, font_size='16sp', background_color=(0.15, 0.55, 0.85, 1))
        cancel_btn = _mk_button(self.cancel_text, font_size='16sp', background_color=(0.40, 0.30, 0.30, 1))
        submit_btn.bind(on_press=self._on_submit)
        cancel_btn.bind(on_press=lambda *_: setattr(self.manager, 'current', 'login'))
        buttons.add_widget(submit_btn)
        buttons.add_widget(cancel_btn)
        return buttons

    def _update_layout(self, *_args):
        metrics = get_viewport_metrics((self.width, self.height))
        mobile = (not metrics.is_landscape) and (not metrics.is_tablet_like)
        pad_x = scaled(14 if mobile else 18, metrics, min_value=10, max_value=28)
        pad_y = scaled(12 if mobile else 16, metrics, min_value=8, max_value=24)
        card_width = min(
            scaled(500 if mobile else 460, metrics, min_value=320, max_value=640),
            max(300, int(self.width - pad_x * 2)),
        )
        self.outer.padding = [pad_x, pad_y, pad_x, pad_y]
        self.card.width = card_width
        self.card.padding = [
            scaled(16 if mobile else 18, metrics, min_value=12, max_value=24),
            scaled(14 if mobile else 16, metrics, min_value=12, max_value=22),
            scaled(16 if mobile else 18, metrics, min_value=12, max_value=24),
            scaled(14 if mobile else 16, metrics, min_value=12, max_value=22),
        ]
        self.card.spacing = scaled(10 if mobile else 12, metrics, min_value=8, max_value=16)
        self.card.height = self.card.minimum_height
        self.outer.height = max(self.height, self.card.height + pad_y * 2 + 24)
        self.title_label.font_size = '22sp' if mobile else '24sp'
        self._apply_layout(metrics, mobile)
        self._reset_scroll()

    def _apply_layout(self, metrics, mobile):
        raise NotImplementedError

    def _on_submit(self, *_args):
        raise NotImplementedError


class LoginScreen(Screen):
    def __init__(self, account_store, on_login_success, **kwargs):
        super().__init__(**kwargs)
        self.store = account_store
        self.on_login_success = on_login_success

        self.scroll = ScrollView(do_scroll_x=False, do_scroll_y=True, bar_width=10, scroll_type=['bars', 'content'])
        self.outer = BoxLayout(orientation='vertical', size_hint_y=None, padding=[16, 16, 16, 16])
        self.outer.bind(minimum_height=self.outer.setter('height'))
        self.scroll.add_widget(self.outer)
        self.card = BoxLayout(orientation='vertical', size_hint=(None, None), spacing=12, padding=[18, 18, 18, 18])
        self.card.bind(minimum_height=self.card.setter('height'))
        _set_block_background(self.card, bg_color=(0.11, 0.17, 0.25, 0.90), border_color=(0.29, 0.39, 0.50, 0.62))
        self.top_spacer = BoxLayout(size_hint_y=1)
        self.bottom_spacer = BoxLayout(size_hint_y=1)
        self.outer.add_widget(self.top_spacer)
        self.outer.add_widget(self.card)
        self.outer.add_widget(self.bottom_spacer)
        self.add_widget(self.scroll)

        self.header = BoxLayout(orientation='vertical', size_hint_y=None, spacing=4, height=112)
        self.title_label = _mk_label('斗兽棋', font_size='30sp', color=hex_to_rgb('#FFD700'), size_hint_y=None, height=40)
        self.subtitle_label = _mk_label('Kivy 跨平台版', font_size='14sp', color=(0.74, 0.82, 0.92, 1), size_hint_y=None, height=22)
        self.deco_label = _mk_label('象 狮 虎 豹 狼 狗 猫 鼠', font_size='14sp', color=hex_to_rgb('#D7B96B'), size_hint_y=None, height=20)
        self.tip_label = _enable_wrap(_mk_label('', font_size='11sp', color=(0.83, 0.83, 0.68, 1), size_hint_y=None, height=24), halign='center')
        self.header.add_widget(self.title_label)
        self.header.add_widget(self.subtitle_label)
        self.header.add_widget(self.deco_label)
        self.header.add_widget(self.tip_label)

        self.form_title = _mk_label('账号登录', font_size='18sp', color=(0.95, 0.95, 0.95, 1), size_hint_y=None, height=24)

        self.username_input = _mk_input(hint='请输入用户名', size_hint_x=1.0)
        self.user_dropdown = DropDown(auto_width=False, width=260)
        self.user_dropdown.bind(on_select=self._on_user_selected)
        self.user_menu_btn = _mk_button('▼', font_size='13sp', size_hint_x=None, width=44, background_color=(0.22, 0.34, 0.46, 1))
        self.user_menu_btn.bind(on_press=self._open_user_dropdown)
        self.username_field = BoxLayout(orientation='horizontal', spacing=6, size_hint_x=0.78)
        self.username_field.add_widget(self.username_input)
        self.username_field.add_widget(self.user_menu_btn)
        self.user_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
        self.user_label = _mk_label('用户名', font_size='14sp', color=(0.72, 0.82, 0.92, 1), size_hint_x=0.22)
        self.user_row.add_widget(self.user_label)
        self.user_row.add_widget(self.username_field)

        self.password_input = _mk_input(hint='请输入密码', password=True, size_hint_x=0.78)
        self.password_input.bind(on_text_validate=self._on_login)
        self.pass_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
        self.pass_label = _mk_label('密码', font_size='14sp', color=(0.72, 0.82, 0.92, 1), size_hint_x=0.22)
        self.pass_row.add_widget(self.pass_label)
        self.pass_row.add_widget(self.password_input)

        self.main_btns = BoxLayout(orientation='horizontal', size_hint_y=None, height=44, spacing=10)
        self.login_btn = _mk_button('登录', font_size='17sp', background_color=(0.15, 0.55, 0.85, 1))
        self.register_btn = _mk_button('注册新账号', font_size='14sp', background_color=(0.2, 0.5, 0.3, 1))
        self.login_btn.bind(on_press=self._on_login)
        self.register_btn.bind(on_press=self._on_goto_register)
        self.main_btns.add_widget(self.login_btn)
        self.main_btns.add_widget(self.register_btn)

        self.minor_btns = BoxLayout(orientation='horizontal', size_hint_y=None, height=36, spacing=8)
        self.change_pwd_btn = _mk_button('修改密码', font_size='12sp', background_color=(0.4, 0.35, 0.25, 1))
        self.reset_pwd_btn = _mk_button('找回密码', font_size='12sp', background_color=(0.4, 0.35, 0.25, 1))
        self.quit_btn = _mk_button('退出', font_size='12sp', background_color=(0.5, 0.2, 0.2, 1))
        self.change_pwd_btn.bind(on_press=self._on_goto_change_pwd)
        self.reset_pwd_btn.bind(on_press=self._on_goto_reset_pwd)
        self.quit_btn.bind(on_press=self._on_quit)
        self.minor_btns.add_widget(self.change_pwd_btn)
        self.minor_btns.add_widget(self.reset_pwd_btn)
        self.minor_btns.add_widget(self.quit_btn)

        for widget in [self.header, self.form_title, self.user_row, self.pass_row, self.main_btns, self.minor_btns]:
            self.card.add_widget(widget)

        self.bind(size=self._update_layout)
        self._update_layout()
        self.refresh_usernames()
        last_user = self.store.get_last_username()
        if last_user:
            self.select_username(last_user)
        self._update_tip()
        Clock.schedule_once(lambda *_: self._reset_scroll(), 0)

    def _reset_scroll(self):
        self.scroll.scroll_y = 1

    def _update_tip(self):
        self.tip_label.text = '已登录过的用户名会被记住' if self.store.has_users() else '首次使用请先注册账号'

    def _update_layout(self, *_args):
        metrics = get_viewport_metrics((self.width, self.height))
        mobile = (not metrics.is_landscape) and (not metrics.is_tablet_like)
        pad_x = scaled(14 if mobile else 18, metrics, min_value=10, max_value=28)
        pad_y = scaled(12 if mobile else 16, metrics, min_value=8, max_value=24)
        card_width = min(
            scaled(500 if mobile else 460, metrics, min_value=320, max_value=640),
            max(300, int(self.width - pad_x * 2)),
        )
        self.outer.padding = [pad_x, pad_y, pad_x, pad_y]
        self.card.width = card_width
        self.card.padding = [
            scaled(16 if mobile else 18, metrics, min_value=12, max_value=24),
            scaled(14 if mobile else 16, metrics, min_value=12, max_value=22),
            scaled(16 if mobile else 18, metrics, min_value=12, max_value=24),
            scaled(14 if mobile else 16, metrics, min_value=12, max_value=22),
        ]
        self.card.spacing = scaled(10 if mobile else 12, metrics, min_value=8, max_value=16)
        self.card.height = self.card.minimum_height
        self.outer.height = max(self.height, self.card.height + pad_y * 2 + 24)
        self.header.height = scaled(112 if mobile else 104, metrics, min_value=96, max_value=140)
        self.title_label.font_size = '24sp' if mobile else '30sp'
        self.subtitle_label.font_size = '13sp' if mobile else '14sp'
        self.deco_label.font_size = '13sp' if mobile else '14sp'
        self.form_title.height = scaled(26 if mobile else 24, metrics, min_value=22, max_value=32)
        row_h = scaled(48 if mobile else 40, metrics, min_value=38, max_value=60)
        btn_h = scaled(50 if mobile else 44, metrics, min_value=40, max_value=64)
        minor_h = scaled(42 if mobile else 36, metrics, min_value=34, max_value=52)
        self.user_row.height = row_h
        self.pass_row.height = row_h
        self.main_btns.height = btn_h
        self.minor_btns.height = minor_h
        self.user_label.size_hint_x = 0.24 if mobile else 0.22
        self.pass_label.size_hint_x = 0.24 if mobile else 0.22
        self.user_menu_btn.width = scaled(48 if mobile else 44, metrics, min_value=40, max_value=60)
        self.user_menu_btn.height = row_h
        self.username_input.height = row_h
        self.password_input.height = row_h
        self._reset_scroll()

    def refresh_usernames(self):
        self.user_dropdown.clear_widgets()
        usernames = self.store.get_usernames()
        self.user_menu_btn.disabled = not bool(usernames)
        for username in usernames:
            item = _mk_button(username, size_hint_y=None, height=40, background_color=(0.16, 0.24, 0.34, 1))
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

    def _on_login(self, *_args):
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

    def _on_goto_register(self, *_args):
        self.manager.current = 'register'

    def _on_goto_change_pwd(self, *_args):
        if not self.store.has_users():
            _show_popup('提示', '当前没有账号，请先注册')
            return
        self.manager.current = 'change_password'

    def _on_goto_reset_pwd(self, *_args):
        if not self.store.has_users():
            _show_popup('提示', '当前没有账号，请先注册')
            return
        self.manager.current = 'reset_password'

    def _on_quit(self, *_args):
        app = App.get_running_app()
        if app:
            app.stop()
        else:
            Window.close()


class RegisterScreen(_BaseFormScreen):
    title_text = '注册新账号'
    tip_text = '首次使用请先注册账号'
    submit_text = '注册'

    def __init__(self, account_store, **kwargs):
        super().__init__(account_store, **kwargs)
        self.username_input = _mk_input(hint='请输入用户名')
        self.password_input = _mk_input(hint='请输入密码', password=True)
        self.confirm_input = _mk_input(hint='请再次输入密码', password=True)
        self.confirm_input.bind(on_text_validate=self._on_submit)
        self.card.add_widget(self._build_header())
        self.card.add_widget(self._build_field_row('用户名', self.username_input))
        self.card.add_widget(self._build_field_row('密码', self.password_input))
        self.card.add_widget(self._build_field_row('确认密码', self.confirm_input))
        self.card.add_widget(self._build_buttons())
        self._update_layout()

    def on_enter(self, *_args):
        self.username_input.text = ''
        self.password_input.text = ''
        self.confirm_input.text = ''
        self._reset_scroll()

    def _apply_layout(self, metrics, mobile):
        pass

    def _on_submit(self, *_args):
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


class ChangePasswordScreen(_BaseFormScreen):
    title_text = '修改密码'
    tip_text = '修改后请使用新密码登录'
    submit_text = '确认修改'

    def __init__(self, account_store, **kwargs):
        super().__init__(account_store, **kwargs)
        self.username_input = _mk_input(hint='请输入用户名')
        self.old_password_input = _mk_input(hint='请输入旧密码', password=True)
        self.new_password_input = _mk_input(hint='请输入新密码', password=True)
        self.confirm_input = _mk_input(hint='请再次输入新密码', password=True)
        self.confirm_input.bind(on_text_validate=self._on_submit)
        self.card.add_widget(self._build_header())
        self.card.add_widget(self._build_field_row('用户名', self.username_input))
        self.card.add_widget(self._build_field_row('旧密码', self.old_password_input))
        self.card.add_widget(self._build_field_row('新密码', self.new_password_input))
        self.card.add_widget(self._build_field_row('确认新密码', self.confirm_input))
        self.card.add_widget(self._build_buttons())
        self._update_layout()

    def on_enter(self, *_args):
        last = self.store.get_last_username()
        if last:
            self.username_input.text = last
        self.old_password_input.text = ''
        self.new_password_input.text = ''
        self.confirm_input.text = ''
        self._reset_scroll()

    def _apply_layout(self, metrics, mobile):
        pass

    def _on_submit(self, *_args):
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


class ResetPasswordScreen(_BaseFormScreen):
    title_text = '找回密码'
    tip_text = f'忘记密码时可使用超级密码找回\n超级密码：{MASTER_PASSWORD}'
    submit_text = '重置密码'

    def __init__(self, account_store, **kwargs):
        super().__init__(account_store, **kwargs)
        self.username_input = _mk_input(hint='请输入用户名')
        self.master_input = _mk_input(hint='请输入超级密码', password=True)
        self.new_password_input = _mk_input(hint='请输入新密码', password=True)
        self.confirm_input = _mk_input(hint='请再次输入新密码', password=True)
        self.confirm_input.bind(on_text_validate=self._on_submit)
        self.card.add_widget(self._build_header())
        self.card.add_widget(self._build_field_row('用户名', self.username_input))
        self.card.add_widget(self._build_field_row('超级密码', self.master_input))
        self.card.add_widget(self._build_field_row('新密码', self.new_password_input))
        self.card.add_widget(self._build_field_row('确认新密码', self.confirm_input))
        self.card.add_widget(self._build_buttons())
        self._update_layout()

    def on_enter(self, *_args):
        last = self.store.get_last_username()
        if last:
            self.username_input.text = last
        self.master_input.text = ''
        self.new_password_input.text = ''
        self.confirm_input.text = ''
        self._reset_scroll()

    def _apply_layout(self, metrics, mobile):
        pass

    def _on_submit(self, *_args):
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
