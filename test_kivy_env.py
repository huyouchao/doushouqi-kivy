"""
斗兽棋 Kivy 版 - 阶段1验证：最小窗口测试
运行此文件，如果弹出一个窗口显示文字，说明 Kivy 环境正常
"""
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window


class JungleChessTestApp(App):
    """最小验证 App，只弹出一个窗口显示确认文字"""

    def build(self):
        # 设置窗口背景色（深绿，与原版一致）
        Window.clearcolor = (0.15, 0.35, 0.15, 1)

        layout = BoxLayout(orientation='vertical', padding=40, spacing=20)

        title = Label(
            text='斗兽棋 Kivy 版',
            font_size='48sp',
            color=(1, 0.84, 0, 1),  # 金色
            bold=True,
            size_hint_y=0.4,
        )

        status = Label(
            text='环境验证成功！\nKivy 已正常安装并运行。',
            font_size='24sp',
            color=(0.2, 0.8, 0.2, 1),  # 绿色
            size_hint_y=0.3,
        )

        info = Label(
            text='Kivy 2.3.1 | Python 3.13.12 | Windows',
            font_size='16sp',
            color=(0.7, 0.7, 0.7, 1),  # 灰色
            size_hint_y=0.3,
        )

        layout.add_widget(title)
        layout.add_widget(status)
        layout.add_widget(info)

        return layout


if __name__ == '__main__':
    JungleChessTestApp().run()