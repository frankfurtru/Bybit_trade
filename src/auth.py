from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Set


@dataclass
class AuthConfig:
    username: str
    password: str
    store_path: str = "data/auth.json"


class AuthStore:
    def __init__(self, cfg: AuthConfig):
        self.cfg = cfg
        self._path = cfg.store_path
        self._authed: Set[int] = set()
        self._ensure_dir()
        self._load()

    def _ensure_dir(self):
        d = os.path.dirname(self._path)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)

    def _load(self):
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            ids = data.get("user_ids") or []
            self._authed = {int(x) for x in ids}
        except Exception:
            self._authed = set()

    def _save(self):
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump({"user_ids": sorted(self._authed)}, f)
        except Exception:
            pass

    def is_authenticated(self, user_id: int) -> bool:
        return user_id in self._authed

    def authenticate(self, user_id: int, username: str, password: str) -> bool:
        if username == self.cfg.username and password == self.cfg.password:
            self._authed.add(user_id)
            self._save()
            return True
        return False

    def logout(self, user_id: int) -> None:
        if user_id in self._authed:
            self._authed.remove(user_id)
            self._save()

