#!/usr/bin/env python3
"""
合浦珠还 - 演示种子数据脚本（幂等）

功能：
  - 创建 3 个演示账号（用户名 demo_ 前缀，密码统一 demo12345）
  - 灌入 10 条真实感校园失物/拾物数据，其中 3 对同类别+同地点+相似描述，
    走真实后端的自动匹配算法产生匹配记录，并将其中 1 对确认为"已解决"
  - 每条数据附一张纯色占位图（标准库 zlib/struct 现场生成 PNG，不加依赖）

运行方式：
  本地：  python3 seed_demo.py            （在 backend/ 下）
          python3 backend/seed_demo.py    （在仓库根下，均可用）
  容器：  docker compose exec hepu python backend/seed_demo.py [--reset]
          数据库/上传目录位置自动与 main.py 保持一致，
          可用 HEPU_DB_PATH / HEPU_UPLOAD_DIR 环境变量覆盖

参数：
  --reset  删除现有数据库与本脚本生成的演示占位图后重新灌入
"""

import argparse
import struct
import sys
import zlib
from datetime import datetime, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))  # 保证任意工作目录下都能 import main

import main as backend  # noqa: E402  复用建表/密码哈希/自动匹配逻辑，与真实后端完全一致

DEMO_PASSWORD = "demo12345"
DEMO_PREFIX = "demo_"

# ---------------- 演示账号 ----------------

USERS = [
    # (username, phone, student_id)
    ("demo_alice", "13800001234", "2023110101"),
    ("demo_bob",   "13800005678", "2023210202"),
    ("demo_carol", "13800009012", "2023330303"),
]

# ---------------- 演示物品 ----------------
# 每条: (key占位图, 归属账号序号, title, category, location, 距今天数, 时刻, description, contact)
# 前 6 条两两配对（同类别 + 相似标题/描述 + 相同地点）→ 触发自动匹配

LOST_ITEMS = [
    dict(key="card", owner=0, title="校园卡",
         category="证件", location="图书馆三楼",
         days=2, hhmm="14:30",
         description="蓝色校园卡，卡面有桂林旅游学院标志，卡号尾号 8823，在图书馆三楼自习室自习结束后遗失",
         contact="微信 alicegmu"),
    dict(key="earphones", owner=2, title="白色蓝牙耳机",
         category="电子产品", location="逸夫楼302教室",
         days=1, hhmm="10:20",
         description="白色蓝牙耳机，充电盒上贴有一张草莓贴纸，上午在逸夫楼302教室上完课后遗失",
         contact="13800009012"),
    dict(key="keys", owner=1, title="一串宿舍钥匙",
         category="钥匙", location="第二食堂二楼",
         days=3, hhmm="18:40",
         description="黑色钥匙扣，挂着三把钥匙和一个图书馆小熊挂件，晚饭时大概落在第二食堂二楼餐区",
         contact="微信 bob_gmu"),
    dict(key="umbrella", owner=2, title="黑色长柄雨伞",
         category="其他", location="鉴水湖畔",
         days=4, hhmm="16:00",
         description="弯钩木质伞柄，伞面内侧绣有姓名缩写 CY，雨后在鉴水湖边的长椅休息时忘记拿走",
         contact="13800009012"),
    dict(key="wallet", owner=0, title="粉色短款钱包",
         category="钱包", location="校园超市门口",
         days=5, hhmm="12:10",
         description="粉色短款钱包，内有身份证和少量现金，最后一次使用是在校园超市门口还共享单车时",
         contact="微信 alicegmu"),
]

FOUND_ITEMS = [
    dict(key="card_found", owner=1, title="捡到一张校园卡",
         category="证件", location="图书馆三楼",
         days=2, hhmm="17:05",
         description="在图书馆三楼自习室桌上捡到一张蓝色校园卡，卡号尾号 8823，请描述办卡时间认领",
         contact="微信 bob_gmu"),
    dict(key="earphones_found", owner=0, title="捡到蓝牙耳机",
         category="电子产品", location="逸夫楼302",
         days=1, hhmm="12:00",
         description="在逸夫楼302教室讲台旁捡到白色蓝牙耳机充电盒，贴纸完好，请描述耳机细节认领",
         contact="微信 alicegmu"),
    dict(key="keys_found", owner=2, title="捡到一串钥匙",
         category="钥匙", location="第二食堂二楼",
         days=3, hhmm="20:15",
         description="在第二食堂二楼餐区桌上捡到一串钥匙，黑色钥匙扣，带一个图书馆小熊挂件",
         contact="13800009012"),
    dict(key="mathbook", owner=1, title="《高等数学》课本",
         category="书籍", location="图书馆四楼",
         days=1, hhmm="19:30",
         description="封面写有王字，内页夹有若干手写笔记，在图书馆四楼考研自习区拾得，请凭笔记内容认领",
         contact="微信 bob_gmu"),
    dict(key="jacket", owner=0, title="深蓝色棒球服外套",
         category="衣物", location="体育馆看台",
         days=1, hhmm="21:00",
         description="男生款 L 码深蓝色棒球服，口袋里有一张电影票根，晚上在体育馆看台拾到",
         contact="微信 alicegmu"),
]


# ---------------- 纯色占位图（标准库生成 PNG，无第三方依赖） ----------------

# 每张占位图的颜色（RGB），与物品一一对应
PLACEHOLDER_COLORS = {
    "card":            (52, 120, 246),
    "card_found":      (28, 90, 200),
    "earphones":       (225, 225, 230),
    "earphones_found": (200, 200, 208),
    "keys":            (122, 96, 62),
    "keys_found":      (96, 74, 48),
    "umbrella":        (31, 58, 110),
    "mathbook":        (46, 139, 87),
    "wallet":          (233, 99, 140),
    "jacket":          (36, 68, 132),
}


def solid_png(rgb, size=64):
    """生成 size x size 纯色 PNG 的字节流（仅用 struct/zlib，无第三方依赖）"""
    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (struct.pack(">I", len(payload)) + tag + payload
                + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)  # 8bit RGB
    row = b"\x00" + bytes(rgb) * size       # 每行: 1 字节滤波类型 0 + 像素
    idat = zlib.compress(row * size)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


def write_placeholder_images() -> int:
    """把演示占位图写入上传目录，返回写入张数（已存在则跳过）"""
    written = 0
    for key, rgb in PLACEHOLDER_COLORS.items():
        path = backend.UPLOAD_DIR / f"{DEMO_PREFIX}{key}.png"
        if not path.exists():
            path.write_bytes(solid_png(rgb))
            written += 1
    return written


def remove_placeholder_images() -> int:
    removed = 0
    for key in PLACEHOLDER_COLORS:
        path = backend.UPLOAD_DIR / f"{DEMO_PREFIX}{key}.png"
        if path.exists():
            path.unlink()
            removed += 1
    return removed


# ---------------- 灌数据 ----------------

def _stamp(days: int, hhmm: str, fmt: str) -> str:
    """生成距今天 days 天、时刻 hhmm 的时间串；fmt 含 %H 用 datetime-local 风格"""
    base = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return f"{base}T{hhmm}" if "%H" in fmt else f"{base} {hhmm}:00"


def _add_item(db, table: str, spec: dict, user_id: int) -> int:
    time_col = "lost_time" if table == "lost_items" else "found_time"
    cur = db.execute(
        f"""INSERT INTO {table}
            (user_id, title, category, location, {time_col}, description, contact, image_url, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, spec["title"], spec["category"], spec["location"],
         _stamp(spec["days"], spec["hhmm"], "%H"),
         spec["description"], spec["contact"],
         f"/uploads/{DEMO_PREFIX}{spec['key']}.png",
         _stamp(spec["days"] + 0, spec["hhmm"], "")))
    item = db.execute(f"SELECT * FROM {table} WHERE id = ?", (cur.lastrowid,)).fetchone()
    backend.auto_match(db, table, item)  # 与真实发布流程一致：插入即触发自动匹配
    return item["id"]


def demo_data_exists() -> bool:
    with backend.get_db() as db:
        rows = db.execute("SELECT username FROM users").fetchall()
    return any(r["username"].startswith(DEMO_PREFIX) for r in rows)


def seed() -> None:
    backend.init_db()  # 幂等建表（--reset 删库后也需要）

    if demo_data_exists():
        print("检测到演示数据已存在，跳过灌入（保持现有数据不变）。")
        print("如需重新灌入： python3 seed_demo.py --reset")
        return

    write_placeholder_images()

    with backend.get_db() as db:
        # 1) 演示账号
        name2id = {}
        for i, (username, phone, student_id) in enumerate(USERS):
            cur = db.execute(
                "INSERT INTO users (username, password, phone, student_id, created_at) VALUES (?, ?, ?, ?, ?)",
                (username, backend.hash_password(DEMO_PASSWORD), phone, student_id,
                 _stamp(6, "09:00", "") if i == 0 else _stamp(5, "21:30", "")))
            name2id[username] = cur.lastrowid

        # 2) 失物/拾物交错插入，后发布的一侧会与前侧自动匹配
        #    顺序：三对配对数据（卡 → 耳机 → 钥匙）+ 两条无对侧的孤品
        for spec in LOST_ITEMS:
            _add_item(db, "lost_items", spec, name2id[USERS[spec["owner"]][0]])
        for spec in FOUND_ITEMS:
            _add_item(db, "found_items", spec, name2id[USERS[spec["owner"]][0]])

        # 3) 把最早产生的一对匹配（校园卡）标记为已确认，让首页呈现"已解决"状态
        first = db.execute(
            "SELECT id, lost_id, found_id FROM matches ORDER BY id ASC LIMIT 1").fetchone()
        if first:
            db.execute("UPDATE matches SET status='confirmed' WHERE id=?", (first["id"],))
            db.execute("UPDATE lost_items SET status='resolved' WHERE id=?", (first["lost_id"],))
            db.execute("UPDATE found_items SET status='resolved' WHERE id=?", (first["found_id"],))

        stats = {
            "users": db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"],
            "lost": db.execute("SELECT COUNT(*) c FROM lost_items").fetchone()["c"],
            "found": db.execute("SELECT COUNT(*) c FROM found_items").fetchone()["c"],
            "matches": db.execute("SELECT COUNT(*) c FROM matches").fetchone()["c"],
        }

    print()
    print("=" * 52)
    print("  合浦珠还 · 演示数据已就绪")
    print("=" * 52)
    print(f"  演示账号（密码统一 {DEMO_PASSWORD}）：")
    for username, _, _ in USERS:
        print(f"    - {username}")
    print(f"  失物 {stats['lost']} 条 · 拾物 {stats['found']} 条 · "
          f"自动匹配 {stats['matches']} 对（含 1 对已确认解决）")
    print(f"  数据库： {backend.DB_PATH}")
    print(f"  占位图： {backend.UPLOAD_DIR}/{DEMO_PREFIX}*.png")
    print("  访问地址： http://127.0.0.1:8000  （容器部署时为主机IP:8000）")
    print("=" * 52)


def reset() -> None:
    if backend.DB_PATH.exists():
        backend.DB_PATH.unlink()
        print(f"已删除数据库： {backend.DB_PATH}")
    else:
        print("数据库文件不存在，无需删除。")
    removed = remove_placeholder_images()
    print(f"已清理演示占位图 {removed} 张。")


def main() -> int:
    parser = argparse.ArgumentParser(description="合浦珠还 - 演示种子数据脚本（幂等）")
    parser.add_argument("--reset", action="store_true", help="删除现有数据库与演示占位图后重新灌入")
    args = parser.parse_args()

    if args.reset:
        reset()
    else:
        seed()
    return 0


if __name__ == "__main__":
    sys.exit(main())
