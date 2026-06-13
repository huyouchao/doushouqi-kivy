# constants.py
# 斗兽棋标准规则常量定义（9x7竖版棋盘）

# 棋盘尺寸
BOARD_ROWS = 9
BOARD_COLS = 7
CELL_SIZE = 70

# 窗口尺寸
WINDOW_WIDTH = BOARD_COLS * CELL_SIZE + 40
WINDOW_HEIGHT = BOARD_ROWS * CELL_SIZE + 120

# 棋子等级映射（从高到低）
# 象(8) > 狮(7) > 虎(6) > 豹(5) > 狼(4) > 狗(3) > 猫(2) > 鼠(1)
PIECE_RANK = {
    '象': 8,
    '狮': 7,
    '虎': 6,
    '豹': 5,
    '狼': 4,
    '狗': 3,
    '猫': 2,
    '鼠': 1
}

# 等级反转映射
RANK_TO_PIECE = {v: k for k, v in PIECE_RANK.items()}

# 动物列表（按等级从高到低）
ANIMALS = ['象', '狮', '虎', '豹', '狼', '狗', '猫', '鼠']

# 河流区域（中间3行，分左右两块水域，每块2列x3行）
# 左侧水域：行3-5，列1-2
# 右侧水域：行3-5，列4-5
# 中间列3为陆地桥梁，可通行
RIVER_CELLS = [
    (3, 1), (3, 2), (4, 1), (4, 2), (5, 1), (5, 2),  # 左侧河流
    (3, 4), (3, 5), (4, 4), (4, 5), (5, 4), (5, 5),  # 右侧河流
]

# 蓝方（上方）兽穴和陷阱
BLUE_DEN = (0, 3)
BLUE_TRAPS = [(0, 2), (0, 4), (1, 3)]

# 红方（下方）兽穴和陷阱
RED_DEN = (8, 3)
RED_TRAPS = [(8, 2), (8, 4), (7, 3)]

# 颜色定义
COLORS = {
    'background': '#1a3a1a',
    'board_line': '#c4a35a',
    'river': '#4a90d9',
    'river_light': '#6bb3f0',
    'trap_blue': '#8b6b8d',
    'trap_red': '#9d6b6b',
    'den_blue': '#2c3e6b',
    'den_red': '#6b2c2c',
    'cell_light': '#2a4a2a',
    'cell_dark': '#1e3a1e',
    'red_piece': '#e74c3c',
    'blue_piece': '#3498db',
    'piece_text': 'white',
    'selected': '#f39c12',
    'valid_move': '#2ecc71',
}

# 初始棋盘布局（9x7标准竖版，中心对称）
# 蓝方在上，红方在下，对应截图中的正确位置
INITIAL_BOARD = [
    # 蓝方（上方，行0-2）
    (0, 0, 'blue', '狮'), (0, 6, 'blue', '虎'),
    (1, 1, 'blue', '狗'), (1, 5, 'blue', '猫'),
    (2, 0, 'blue', '鼠'), (2, 2, 'blue', '豹'), (2, 4, 'blue', '狼'), (2, 6, 'blue', '象'),
    # 红方（下方，行6-8）
    (6, 0, 'red', '象'), (6, 2, 'red', '狼'), (6, 4, 'red', '豹'), (6, 6, 'red', '鼠'),
    (7, 1, 'red', '猫'), (7, 5, 'red', '狗'),
    (8, 0, 'red', '虎'), (8, 6, 'red', '狮'),
]
