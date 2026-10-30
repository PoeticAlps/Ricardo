"""
合浦珠还 - 校园失物招领平台后端
FastAPI + SQLite（标准库 sqlite3，无 ORM）
契约 100% 依照前端 static/js/app.js：统一返回 {code, msg, data}，成功 code=200，
未登录 code=401（HTTP 层始终 200，前端只看响应体里的 code）。
"""

import hashlib, os, re, secrets, sqlite3, uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent   # backend/
ROOT_DIR = BASE_DIR.parent                   # 仓库根（前端所在目录）
DB_PATH = BASE_DIR / "hepu.db"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

IMG_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}; MAX_IMG = 5 * 1024 * 1024  # 5MB

app = FastAPI(title="合浦珠还 - 校园失物招领平台")


# ============ 数据库 ============

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as db:
        # status 约定: 物品 pending待匹配/matched已有匹配/resolved已解决；匹配 pending/confirmed/rejected
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL, phone TEXT DEFAULT '', student_id TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime')));  -- password格式: salt$pbkdf2哈希
        CREATE TABLE IF NOT EXISTS tokens (
            token TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS lost_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id),
            title TEXT NOT NULL, category TEXT DEFAULT '', location TEXT DEFAULT '',
            lost_time TEXT DEFAULT '', description TEXT DEFAULT '', contact TEXT DEFAULT '',
            image_url TEXT DEFAULT '', status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS found_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id),
            title TEXT NOT NULL, category TEXT DEFAULT '', location TEXT DEFAULT '',
            found_time TEXT DEFAULT '', description TEXT DEFAULT '', contact TEXT DEFAULT '',
            image_url TEXT DEFAULT '', status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lost_id INTEGER NOT NULL REFERENCES lost_items(id),
            found_id INTEGER NOT NULL REFERENCES found_items(id),
            score REAL NOT NULL,               -- 0~1，前端按 Math.round(score*100) 显示百分比
            status TEXT DEFAULT 'pending', created_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE (lost_id, found_id));
        """)


init_db()


# ============ 通用工具 ============

def ok(data=None, msg="ok"):
    return {"code": 200, "msg": msg, "data": data}

def fail(msg, code=400):
    return {"code": code, "msg": msg, "data": None}


def hash_password(password: str) -> str:
    """PBKDF2-SHA256 加盐哈希，格式 salt$hash"""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    calc = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return secrets.compare_digest(calc, digest)


def current_user(request: Request):
    """从 Authorization: Bearer <token> 解析当前用户，未登录返回 None"""
    auth = request.headers.get("authorization", "")
    token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    if not token:
        return None
    with get_db() as db:
        return db.execute(
            "SELECT u.* FROM tokens t JOIN users u ON u.id = t.user_id WHERE t.token = ?",
            (token,)).fetchone()


def row_dict(row):
    return dict(row) if row is not None else None


def card_fields(row) -> dict:
    """列表/搜索卡片所需字段"""
    return {"id": row["id"], "title": row["title"], "description": row["description"],
            "location": row["location"], "image_url": row["image_url"],
            "status": row["status"], "created_at": row["created_at"]}


async def save_image(image) -> str:
    """保存上传图片到 backend/uploads/，返回可访问 URL；无图/非法返回空串"""
    if image is None or not image.filename:
        return ""
    ext = os.path.splitext(image.filename)[1].lower()
    if ext not in IMG_EXT:
        return ""
    data = await image.read()
    if not data or len(data) > MAX_IMG:
        return ""
    name = f"{uuid.uuid4().hex}{ext}"
    (UPLOAD_DIR / name).write_bytes(data)
    return f"/uploads/{name}"


# ============ 简单文本匹配算法 ============

def _bigrams(text: str) -> set:
    """中文无分词，用字符二元组做相似度"""
    text = re.sub(r"\s+", "", text or "")
    return {text[i:i + 2] for i in range(len(text) - 1)} or ({text} if text else set())


def calc_score(lost, found) -> float:
    """类别必须相同；得分 = 0.5(类别) + 0.3*文本相似度 + 0.2*地点相似度"""
    if not lost["category"] or lost["category"] != found["category"]:
        return 0.0
    la = _bigrams(lost["title"] + (lost["description"] or ""))
    fa = _bigrams(found["title"] + (found["description"] or ""))
    text_sim = len(la & fa) / len(la | fa) if la and fa else 0.0
    ll, fl = lost["location"] or "", found["location"] or ""
    loc_sim = 1.0 if ll and fl and (ll in fl or fl in ll or (_bigrams(ll) & _bigrams(fl))) else 0.0
    return round(0.5 + 0.3 * text_sim + 0.2 * loc_sim, 2)


def auto_match(db, table: str, item):
    """新发布一条物品后，与另一侧的待解决物品两两计算得分，写入 matches"""
    other = "found_items" if table == "lost_items" else "lost_items"
    for cand in db.execute(
            f"SELECT * FROM {other} WHERE status != 'resolved' ORDER BY id DESC LIMIT 200"):
        score = calc_score(item, cand)
        if score < 0.55:  # 同类别(0.5)之上还需文本或地点有交集
            continue
        lost, found = (item, cand) if table == "lost_items" else (cand, item)
        db.execute("INSERT OR IGNORE INTO matches (lost_id, found_id, score) VALUES (?, ?, ?)",
                   (lost["id"], found["id"], score))
        db.execute("UPDATE lost_items SET status='matched' WHERE id=? AND status='pending'", (lost["id"],))
        db.execute("UPDATE found_items SET status='matched' WHERE id=? AND status='pending'", (found["id"],))


# ============ 认证接口 ============

@app.post("/api/register")
async def register(request: Request):
    body = await request.json()
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    if not username or not password:
        return fail("用户名和密码不能为空")
    if len(password) < 6:
        return fail("密码至少 6 位")
    with get_db() as db:
        if db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
            return fail("用户名已存在")
        db.execute("INSERT INTO users (username, password, phone, student_id) VALUES (?, ?, ?, ?)",
                   (username, hash_password(password),
                    (body.get("phone") or "").strip(), (body.get("student_id") or "").strip()))
    return ok(msg="注册成功")


@app.post("/api/login")
async def login(request: Request):
    body = await request.json()
    username = (body.get("username") or "").strip()
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user is None or not verify_password(body.get("password") or "", user["password"]):
            return fail("用户名或密码错误")
        token = secrets.token_hex(32)
        db.execute("INSERT INTO tokens (token, user_id) VALUES (?, ?)", (token, user["id"]))
        # 前端把整个 data 当作用户对象使用（result.data.username 等）
        return ok(msg="登录成功", data={"token": token, "id": user["id"], "username": user["username"],
                                       "phone": user["phone"], "student_id": user["student_id"]})


# ============ 列表 / 详情 ============

def _list_items(table: str, page: int, per_page: int):
    page, per_page = max(page, 1), min(max(per_page, 1), 50)
    with get_db() as db:
        rows = db.execute(f"SELECT * FROM {table} ORDER BY id DESC LIMIT ? OFFSET ?",
                          (per_page, (page - 1) * per_page)).fetchall()
        total = db.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"]
    return ok(data={"items": [card_fields(r) for r in rows],
                    "total": total, "page": page, "per_page": per_page})


def _detail(table: str, item_id: int):
    with get_db() as db:
        row = db.execute(f"SELECT * FROM {table} WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            return fail("物品不存在", 404)
        user = db.execute("SELECT username FROM users WHERE id = ?", (row["user_id"],)).fetchone()
    data = row_dict(row)
    data["user"] = {"username": user["username"] if user else "未知"}
    return ok(data=data)


@app.get("/api/lost/list")
async def lost_list(page: int = 1, per_page: int = 10):
    return _list_items("lost_items", page, per_page)


@app.get("/api/found/list")
async def found_list(page: int = 1, per_page: int = 10):
    return _list_items("found_items", page, per_page)


@app.get("/api/lost/{item_id}")
async def lost_detail(item_id: int):
    return _detail("lost_items", item_id)


@app.get("/api/found/{item_id}")
async def found_detail(item_id: int):
    return _detail("found_items", item_id)


# ============ 发布（multipart 表单，含可选图片） ============

async def _publish(request: Request, table: str, time_col: str):
    user = current_user(request)
    if user is None:
        return fail("请先登录", 401)
    form = await request.form()
    title = (form.get("title") or "").strip()
    if not title:
        return fail("物品名称不能为空")
    image_url = await save_image(form.get("image"))
    with get_db() as db:
        cur = db.execute(
            f"""INSERT INTO {table}
                (user_id, title, category, location, {time_col}, description, contact, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user["id"], title, (form.get("category") or "").strip(),
             (form.get("location") or "").strip(), (form.get(time_col) or "").strip(),
             (form.get("description") or "").strip(), (form.get("contact") or "").strip(), image_url))
        item = db.execute(f"SELECT * FROM {table} WHERE id = ?", (cur.lastrowid,)).fetchone()
        auto_match(db, table, item)  # 发布后立即尝试与另一侧物品匹配
    return ok(msg="发布成功")


@app.post("/api/lost")
async def publish_lost(request: Request):
    return await _publish(request, "lost_items", "lost_time")


@app.post("/api/found")
async def publish_found(request: Request):
    return await _publish(request, "found_items", "found_time")


# ============ 搜索 ============

@app.get("/api/search")
async def search(q: str = ""):
    q = q.strip()
    if not q:
        return ok(data={"lost": [], "found": []})
    like = f"%{q}%"
    cond = "title LIKE ? OR description LIKE ? OR location LIKE ?"
    args = (like, like, like)
    with get_db() as db:
        lost = db.execute(f"SELECT * FROM lost_items WHERE {cond} ORDER BY id DESC LIMIT 20", args).fetchall()
        found = db.execute(f"SELECT * FROM found_items WHERE {cond} ORDER BY id DESC LIMIT 20", args).fetchall()
    return ok(data={"lost": [card_fields(r) for r in lost], "found": [card_fields(r) for r in found]})


# ============ 匹配 ============

def _match_view(db, m):
    lost = db.execute("SELECT * FROM lost_items WHERE id = ?", (m["lost_id"],)).fetchone()
    found = db.execute("SELECT * FROM found_items WHERE id = ?", (m["found_id"],)).fetchone()
    return {"id": m["id"], "score": m["score"], "status": m["status"], "created_at": m["created_at"],
            "lost_item": {"id": lost["id"], "title": lost["title"], "location": lost["location"]} if lost else {},
            "found_item": {"id": found["id"], "title": found["title"], "location": found["location"]} if found else {}}


def _my_matches(db, user_id: int):
    """当前用户作为失物方或拾物方参与的全部匹配"""
    rows = db.execute("""SELECT m.* FROM matches m
                         JOIN lost_items l ON l.id = m.lost_id
                         JOIN found_items f ON f.id = m.found_id
                         WHERE l.user_id = ? OR f.user_id = ? ORDER BY m.id DESC""",
                      (user_id, user_id)).fetchall()
    return [_match_view(db, m) for m in rows]


def _is_participant(user, lost_id: int, found_id: int) -> bool:
    with get_db() as db:
        lost = db.execute("SELECT user_id FROM lost_items WHERE id = ?", (lost_id,)).fetchone()
        found = db.execute("SELECT user_id FROM found_items WHERE id = ?", (found_id,)).fetchone()
    return bool(lost and found and user["id"] in (lost["user_id"], found["user_id"]))


@app.get("/api/match/list")
async def match_list(request: Request):
    user = current_user(request)
    if user is None:
        return fail("请先登录", 401)
    with get_db() as db:
        return ok(data=_my_matches(db, user["id"]))


@app.post("/api/match/{match_id}/confirm")
async def match_confirm(match_id: int, request: Request):
    user = current_user(request)
    if user is None:
        return fail("请先登录", 401)
    with get_db() as db:
        m = db.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
        if m is None:
            return fail("匹配记录不存在", 404)
        if not _is_participant(user, m["lost_id"], m["found_id"]):
            return fail("无权操作该匹配", 403)
        db.execute("UPDATE matches SET status='confirmed' WHERE id=?", (match_id,))
        db.execute("UPDATE lost_items SET status='resolved' WHERE id=?", (m["lost_id"],))
        db.execute("UPDATE found_items SET status='resolved' WHERE id=?", (m["found_id"],))
    return ok(msg="匹配已确认")


@app.post("/api/match/{match_id}/reject")
async def match_reject(match_id: int, request: Request):
    user = current_user(request)
    if user is None:
        return fail("请先登录", 401)
    with get_db() as db:
        m = db.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
        if m is None:
            return fail("匹配记录不存在", 404)
        if not _is_participant(user, m["lost_id"], m["found_id"]):
            return fail("无权操作该匹配", 403)
        db.execute("UPDATE matches SET status='rejected' WHERE id=?", (match_id,))
    return ok(msg="已忽略该匹配")


# ============ 个人中心 ============

@app.get("/api/user/profile")
async def user_profile(request: Request):
    user = current_user(request)
    if user is None:
        return fail("请先登录", 401)
    with get_db() as db:
        lost_count = db.execute("SELECT COUNT(*) AS c FROM lost_items WHERE user_id=?", (user["id"],)).fetchone()["c"]
        found_count = db.execute("SELECT COUNT(*) AS c FROM found_items WHERE user_id=?", (user["id"],)).fetchone()["c"]
        match_count = len(_my_matches(db, user["id"]))
    return ok(data={"id": user["id"], "username": user["username"], "phone": user["phone"],
                    "student_id": user["student_id"], "lost_count": lost_count,
                    "found_count": found_count, "match_count": match_count})


@app.get("/api/user/items")
async def user_items(request: Request):
    user = current_user(request)
    if user is None:
        return fail("请先登录", 401)
    with get_db() as db:
        cols = "id, title, status, created_at"
        lost = db.execute(f"SELECT {cols} FROM lost_items WHERE user_id=? ORDER BY id DESC", (user["id"],)).fetchall()
        found = db.execute(f"SELECT {cols} FROM found_items WHERE user_id=? ORDER BY id DESC", (user["id"],)).fetchall()
    return ok(data={"lost": [row_dict(r) for r in lost], "found": [row_dict(r) for r in found]})


# ============ 静态托管（先 API 后静态，最后根路径回 index.html） ============

app.mount("/static", StaticFiles(directory=ROOT_DIR / "static"), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
async def index():
    return FileResponse(ROOT_DIR / "index.html")
