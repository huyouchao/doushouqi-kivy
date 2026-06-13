"""
auth_logic.py - 账号系统纯逻辑（从原版 auth.py 提取，去掉 PyQt5 依赖）
AccountStore 类：账号注册、登录验证、密码修改/重置、积分记录
"""
import hashlib
import json
import os
import uuid

from platform_services.storage import get_accounts_file


MASTER_PASSWORD = "123."
ACCOUNT_FILE_NAME = "user_accounts.json"


def hash_password(password):
    """SHA256 哈希密码"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class AccountStore:
    def __init__(self, file_path=None):
        self.file_path = file_path or get_accounts_file()
        self.data = self._load()

    def _default_data(self):
        return {
            "users": {},
            "remembered_users": [],
            "last_username": "",
            "score_history": [],
            "window_preferences": {},
        }

    def _load(self):
        if not os.path.exists(self.file_path):
            return self._default_data()

        try:
            with open(self.file_path, "r", encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError):
            return self._default_data()

        data = self._default_data()
        users = payload.get("users", {})
        if isinstance(users, dict):
            for username, user_data in users.items():
                if not isinstance(username, str) or not isinstance(user_data, dict):
                    continue
                password_hash = user_data.get("password_hash")
                if isinstance(password_hash, str) and password_hash:
                    data["users"][username] = {"password_hash": password_hash}

        remembered_users = payload.get("remembered_users", [])
        if isinstance(remembered_users, list):
            seen = set()
            for username in remembered_users:
                if (
                    isinstance(username, str)
                    and username in data["users"]
                    and username not in seen
                ):
                    data["remembered_users"].append(username)
                    seen.add(username)

        last_username = payload.get("last_username", "")
        if isinstance(last_username, str) and last_username in data["users"]:
            data["last_username"] = last_username

        score_history = payload.get("score_history", [])
        if isinstance(score_history, list):
            for entry in score_history:
                if not isinstance(entry, dict):
                    continue
                username = entry.get("username")
                if not isinstance(username, str) or username not in data["users"]:
                    continue
                normalized_entry = {
                    "id": str(entry.get("id") or uuid.uuid4().hex),
                    "username": username,
                    "played_at": str(entry.get("played_at", "")),
                    "difficulty_label": str(entry.get("difficulty_label", "")),
                    "player_seconds": int(entry.get("player_seconds", 0) or 0),
                    "ai_seconds": int(entry.get("ai_seconds", 0) or 0),
                    "game_score": int(entry.get("game_score", 0) or 0),
                    "cumulative_score": int(entry.get("cumulative_score", 0) or 0),
                }
                data["score_history"].append(normalized_entry)

        window_preferences = payload.get("window_preferences", {})
        if isinstance(window_preferences, dict):
            for username, size_data in window_preferences.items():
                if username not in data["users"] or not isinstance(size_data, dict):
                    continue
                width = size_data.get("width")
                height = size_data.get("height")
                if isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0:
                    data["window_preferences"][username] = {"width": width, "height": height}

        self._recalculate_all_cumulative_scores(data)

        return data

    def _recalculate_all_cumulative_scores(self, target_data=None):
        data = target_data if target_data is not None else self.data
        totals = {}
        for entry in data["score_history"]:
            username = entry["username"]
            totals[username] = totals.get(username, 0) + max(0, int(entry.get("game_score", 0)))
            entry["cumulative_score"] = totals[username]

    def save(self):
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as file:
            json.dump(self.data, file, ensure_ascii=False, indent=2)

    def has_users(self):
        return bool(self.data["users"])

    def user_exists(self, username):
        return username in self.data["users"]

    def get_usernames(self):
        ordered = list(self.data["remembered_users"])
        for username in sorted(self.data["users"]):
            if username not in ordered:
                ordered.append(username)
        return ordered

    def get_last_username(self):
        return self.data.get("last_username", "")

    def get_total_score(self, username):
        username = username.strip()
        total = 0
        for entry in self.data["score_history"]:
            if entry["username"] == username:
                total += max(0, int(entry.get("game_score", 0)))
        return total

    def get_window_size(self, username):
        username = username.strip()
        size_data = self.data["window_preferences"].get(username)
        if not isinstance(size_data, dict):
            return None
        width = size_data.get("width")
        height = size_data.get("height")
        if not isinstance(width, int) or not isinstance(height, int):
            return None
        if width <= 0 or height <= 0:
            return None
        return width, height

    def register_user(self, username, password):
        username = username.strip()
        if not username:
            raise ValueError("用户名不能为空。")
        if not password:
            raise ValueError("密码不能为空。")
        if self.user_exists(username):
            raise ValueError("该用户名已存在，请更换用户名。")

        self.data["users"][username] = {"password_hash": hash_password(password)}
        self.save()

    def verify_login(self, username, password):
        username = username.strip()
        if not username or not password:
            return False
        user_data = self.data["users"].get(username)
        if not user_data:
            return False
        return user_data["password_hash"] == hash_password(password)

    def remember_username(self, username):
        username = username.strip()
        if not self.user_exists(username):
            return

        remembered = [item for item in self.data["remembered_users"] if item != username]
        remembered.insert(0, username)
        self.data["remembered_users"] = remembered
        self.data["last_username"] = username
        self.save()

    def change_password(self, username, old_password, new_password):
        username = username.strip()
        if not self.user_exists(username):
            raise ValueError("用户名不存在。")
        if not old_password:
            raise ValueError("请输入旧密码。")
        if not new_password:
            raise ValueError("新密码不能为空。")
        if not self.verify_login(username, old_password):
            raise ValueError("旧密码不正确。")

        self.data["users"][username]["password_hash"] = hash_password(new_password)
        self.save()

    def reset_password_with_master(self, username, master_password, new_password):
        username = username.strip()
        if not self.user_exists(username):
            raise ValueError("用户名不存在。")
        if master_password != MASTER_PASSWORD:
            raise ValueError("超级密码不正确。")
        if not new_password:
            raise ValueError("新密码不能为空。")

        self.data["users"][username]["password_hash"] = hash_password(new_password)
        self.save()

    def save_window_size(self, username, width, height):
        username = username.strip()
        if not self.user_exists(username):
            raise ValueError("用户名不存在。")
        width = int(width)
        height = int(height)
        if width <= 0 or height <= 0:
            raise ValueError("窗口尺寸不正确。")

        self.data["window_preferences"][username] = {"width": width, "height": height}
        self.save()

    def clear_window_size(self, username):
        username = username.strip()
        if username in self.data["window_preferences"]:
            del self.data["window_preferences"][username]
            self.save()

    def add_score_entry(
        self,
        username,
        played_at,
        difficulty_label,
        player_seconds,
        ai_seconds,
        game_score,
    ):
        username = username.strip()
        if not self.user_exists(username):
            raise ValueError("用户名不存在。")

        score = max(0, min(100, int(game_score)))
        cumulative_score = self.get_total_score(username) + score
        entry = {
            "id": uuid.uuid4().hex,
            "username": username,
            "played_at": played_at,
            "difficulty_label": difficulty_label,
            "player_seconds": max(0, int(player_seconds)),
            "ai_seconds": max(0, int(ai_seconds)),
            "game_score": score,
            "cumulative_score": cumulative_score,
        }
        self.data["score_history"].append(entry)
        self.save()
        return dict(entry)

    def get_score_history(self, username=None):
        normalized_username = username.strip() if isinstance(username, str) else ""
        entries = []
        for entry in self.data["score_history"]:
            if normalized_username and entry["username"] != normalized_username:
                continue
            entries.append(dict(entry))
        entries.sort(key=lambda item: item.get("played_at", ""), reverse=True)
        return entries

    def delete_score_entry(self, entry_id, master_password):
        if master_password != MASTER_PASSWORD:
            raise ValueError("超级密码不正确。")

        original_length = len(self.data["score_history"])
        self.data["score_history"] = [
            entry for entry in self.data["score_history"] if entry.get("id") != entry_id
        ]
        if len(self.data["score_history"]) == original_length:
            raise ValueError("未找到要删除的积分项。")

        self._recalculate_all_cumulative_scores()
        self.save()
