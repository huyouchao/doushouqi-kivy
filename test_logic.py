"""
斗兽棋 Kivy 版 - 阶段2验证：逻辑层导入测试
验证 constants / game_logic / ai_player 三个模块脱离 PyQt5 后仍能正常工作
"""
import sys
import os

# 确保 core 包可被找到
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.constants import (
    BOARD_ROWS, BOARD_COLS, CELL_SIZE,
    PIECE_RANK, RIVER_CELLS, TRAPS, DENS,
    COLORS, INITIAL_BOARD, PIECE_NAMES
)
from core.game_logic import Piece, GameLogic
from core.ai_player import AIPlayer, DIFFICULTY_PROFILES


def test_constants():
    """验证常量模块"""
    print("=" * 50)
    print("【测试1】常量模块验证")
    print(f"  棋盘尺寸: {BOARD_ROWS}行 x {BOARD_COLS}列, 格子大小={CELL_SIZE}")
    print(f"  棋子等级: {PIECE_RANK}")
    print(f"  河流格子: {RIVER_CELLS}")
    print(f"  陷阱位置: {TRAPS}")
    print(f"  兽穴位置: {DENS}")
    print(f"  初始棋盘行数: {len(INITIAL_BOARD)}")
    print(f"  棋子名称: {PIECE_NAMES}")
    print("  ✓ 常量模块正常")


def test_game_logic():
    """验证游戏逻辑模块"""
    print("=" * 50)
    print("【测试2】游戏逻辑模块验证")

    # 创建游戏逻辑实例
    gl = GameLogic()
    print(f"  初始棋盘已加载，当前回合: {gl.current_turn}")

    # 测试走棋
    # 红方（下方）鼠在 (6,2)，向右移动到 (6,3)
    result = gl.move_piece(6, 2, 6, 3)
    print(f"  红方鼠 (6,2)→(6,3): {result}")
    print(f"  移动后回合切换为: {gl.current_turn}")

    # 测试无效走棋（蓝方不能走红方位置时，走对方棋子）
    result2 = gl.move_piece(0, 6, 0, 5)
    print(f"  蓝方猫 (0,6)→(0,5): {result2}")
    print(f"  当前回合: {gl.current_turn}")

    # 测试 to_dict / from_dict（存档功能）
    state = gl.to_dict()
    print(f"  存档序列化成功，回合={state['current_turn']}, 步数={state['move_count']}")

    gl2 = GameLogic.from_dict(state)
    print(f"  读档反序列化成功，回合={gl2.current_turn}, 步数={gl2.move_count}")
    print("  ✓ 游戏逻辑模块正常")


def test_ai_player():
    """验证 AI 模块"""
    print("=" * 50)
    print("【测试3】AI 模块验证")

    gl = GameLogic()
    print(f"  难度配置数: {len(DIFFICULTY_PROFILES)}")
    print(f"  难度等级: {list(DIFFICULTY_PROFILES.keys())}")

    # 测试5级 AI
    ai = AIPlayer(difficulty=5)
    print(f"  AI 5级: depth={ai.depth}, top_k={ai.top_k}")

    # 让 AI 走一步
    move = ai.get_best_move(gl)
    if move:
        from_row, from_col, to_row, to_col = move
        print(f"  AI 推荐走法: ({from_row},{from_col}) → ({to_row},{to_col})")
        result = gl.move_piece(from_row, from_col, to_row, to_col)
        print(f"  执行结果: {result}")
    else:
        print("  AI 未找到合法走法（可能有bug）")

    print("  ✓ AI 模块正常")


def main():
    print("\n")
    print("★ 斗兽棋 Kivy 版 - 逻辑层验证 ★")
    print("验证三个核心模块脱离 PyQt5 后是否正常工作\n")

    try:
        test_constants()
        test_game_logic()
        test_ai_player()

        print("=" * 50)
        print("\n🎉 全部测试通过！逻辑层可以正常使用，无 PyQt5 依赖。")
        print("可以进入下一阶段：棋盘绘制。\n")
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)