"""
SQLite 数据持久化模块

替代内存存储，支持历史记录、趋势分析等。
"""

import sqlite3
import json
import uuid
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from contextlib import contextmanager
import os


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ita_data.db")


class Database:
    """SQLite 数据库管理"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_tables()

    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_tables(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_records (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    ita REAL NOT NULL,
                    category TEXT NOT NULL,
                    fitzpatrick TEXT,
                    description TEXT,
                    color_hex TEXT,
                    confidence REAL,
                    lab_l REAL,
                    lab_a REAL,
                    lab_b REAL,
                    white_mean_rgb TEXT,
                    skin_mean_rgb TEXT,
                    normalized_rgb TEXT,
                    uv_index REAL,
                    location TEXT,
                    vitd_advice TEXT
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_records_created_at
                ON analysis_records(created_at)
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

    def save_analysis(self, record: Dict) -> str:
        """
        保存一条分析记录

        Args:
            record: 分析结果字典

        Returns:
            记录 ID
        """
        record_id = record.get("id", str(uuid.uuid4())[:8])
        now = datetime.now().isoformat()

        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO analysis_records (
                    id, created_at, ita, category, fitzpatrick, description,
                    color_hex, confidence, lab_l, lab_a, lab_b,
                    white_mean_rgb, skin_mean_rgb, normalized_rgb,
                    uv_index, location, vitd_advice
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record_id,
                now,
                record.get("ita"),
                record.get("category"),
                record.get("fitzpatrick"),
                record.get("description"),
                record.get("color_hex"),
                record.get("confidence"),
                record.get("lab", {}).get("L"),
                record.get("lab", {}).get("a"),
                record.get("lab", {}).get("b"),
                json.dumps(record.get("calibration", {}).get("white_mean_rgb")),
                json.dumps(record.get("calibration", {}).get("skin_mean_rgb")),
                json.dumps(record.get("calibration", {}).get("normalized_rgb")),
                record.get("uv_index"),
                record.get("location"),
                json.dumps(record.get("vitd_advice")) if record.get("vitd_advice") else None
            ))

        return record_id

    def get_record(self, record_id: str) -> Optional[Dict]:
        """获取单条记录"""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM analysis_records WHERE id = ?", (record_id,)
            ).fetchone()

            if row is None:
                return None

            return self._row_to_dict(row)

    def get_recent_records(self, limit: int = 20) -> List[Dict]:
        """获取最近的分析记录"""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM analysis_records ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()

            return [self._row_to_dict(row) for row in rows]

    def get_records_by_date_range(
        self,
        start_date: str,
        end_date: Optional[str] = None
    ) -> List[Dict]:
        """获取日期范围内的记录"""
        if end_date is None:
            end_date = datetime.now().isoformat()

        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM analysis_records WHERE created_at >= ? AND created_at <= ? ORDER BY created_at DESC",
                (start_date, end_date)
            ).fetchall()

            return [self._row_to_dict(row) for row in rows]

    def get_ita_trend(self, days: int = 30) -> Dict:
        """
        获取 ITA° 趋势数据

        Args:
            days: 天数

        Returns:
            趋势数据字典
        """
        start_date = (datetime.now() - timedelta(days=days)).isoformat()

        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT created_at, ita, category FROM analysis_records "
                "WHERE created_at >= ? ORDER BY created_at ASC",
                (start_date,)
            ).fetchall()

        records = [{"date": r["created_at"], "ita": r["ita"], "category": r["category"]} for r in rows]

        if not records:
            return {"records": [], "stats": None, "days": days}

        ita_values = [r["ita"] for r in records]
        stats = {
            "count": len(ita_values),
            "latest": ita_values[-1],
            "earliest": ita_values[0],
            "average": round(sum(ita_values) / len(ita_values), 1),
            "min": round(min(ita_values), 1),
            "max": round(max(ita_values), 1),
            "change": round(ita_values[-1] - ita_values[0], 1),
        }

        return {
            "records": records,
            "stats": stats,
            "days": days
        }

    def get_record_count(self) -> int:
        """获取总记录数"""
        with self.get_connection() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM analysis_records").fetchone()
            return row["cnt"]

    def delete_record(self, record_id: str) -> bool:
        """删除一条记录"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM analysis_records WHERE id = ?", (record_id,)
            )
            return cursor.rowcount > 0

    def save_setting(self, key: str, value: str):
        """保存用户设置"""
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_settings (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, now))

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """获取用户设置"""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM user_settings WHERE key = ?", (key,)
            ).fetchone()
            return row["value"] if row else default

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict:
        """将数据库行转换为字典"""
        d = dict(row)
        # 解析 JSON 字段
        for json_field in ["white_mean_rgb", "skin_mean_rgb", "normalized_rgb", "vitd_advice"]:
            if d.get(json_field):
                try:
                    d[json_field] = json.loads(d[json_field])
                except (json.JSONDecodeError, TypeError):
                    pass
        # 重组 lab 字段
        if d.get("lab_l") is not None:
            d["lab"] = {
                "L": d.pop("lab_l"),
                "a": d.pop("lab_a"),
                "b": d.pop("lab_b"),
            }
        return d


# 全局数据库实例
_db_instance: Optional[Database] = None


def get_database() -> Database:
    """获取全局数据库实例（单例模式）"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
