# 合浦珠还——校园失物招领平台

> "假如我们都有掉东西的时候" —— 专为桂林旅游学院师生打造的失物招领平台。

纯前端界面 + FastAPI/SQLite 后端，一键启动即可完整使用：注册登录、发布失物/拾物（支持图片上传）、
发布时自动按"类别 + 文本相似度 + 地点"智能匹配、关键词搜索、个人中心统计。

## 功能列表

- 用户注册 / 登录（PBKDF2 加盐密码哈希，Bearer Token 鉴权）
- 发布失物信息、发布拾物信息（multipart 表单，支持上传图片，存于 `backend/uploads/`）
- 首页最新失物 / 拾物列表（分页）
- 物品详情页（发布者、联系方式、图片）
- 关键词搜索（标题 / 描述 / 地点，同时覆盖失物与拾物）
- 自动匹配：发布物品后立即与另一侧物品计算匹配度（0~100%），双方均可在"匹配记录"中确认或忽略
- 匹配确认后双方物品标记为"已解决"，个人中心展示发布数与匹配数统计

## 一键启动

```bash
./backend/run.sh
```

脚本会自动创建虚拟环境（`backend/venv/`）、安装依赖并启动服务，然后浏览器打开：

**http://127.0.0.1:8000**

## 默认演示路径

1. 打开首页 → 注册两个账号（如 alice / bob，密码至少 6 位）
2. alice 登录 → "我丢东西了" 发布一条失物（例：钱包 / 图书馆三楼）
3. bob 登录 → "我捡到东西了" 发布一条相近的拾物（同类别 + 相似标题/地点）
4. 任一账号进入"匹配记录" → 看到自动生成的匹配（含匹配度百分比）→ 确认匹配
5. 回到首页列表可看到物品状态变为"已解决"；个人中心可查看发布与匹配统计

## 技术栈

- 前端：原生 HTML/CSS/JavaScript（无构建步骤），Font Awesome CDN 图标
- 后端：FastAPI + uvicorn + 标准库 sqlite3（无 ORM）
- 密码：`hashlib.pbkdf2_hmac` SHA-256 加盐哈希（10 万轮迭代）
- 数据库：SQLite 单文件 `backend/hepu.db`（首次启动自动建表）
- 图片：上传至 `backend/uploads/`，经 `/uploads/...` 静态服务
- 部署形态：后端同源托管前端（`/` 返回 index.html，`/static/...` 静态资源），无需 CORS

## 目录结构

```
.
├── index.html              # 前端单页
├── static/
│   ├── css/style.css       # 样式
│   └── js/app.js           # 前端逻辑
├── backend/
│   ├── main.py             # FastAPI 应用（API + 静态托管 + 建表）
│   ├── requirements.txt    # fastapi / uvicorn / python-multipart
│   ├── run.sh              # 一键启动脚本
│   ├── .gitignore          # 排除 venv/ db/ uploads/ 等运行时产物
│   ├── hepu.db             # （运行时生成）SQLite 数据库
│   └── uploads/            # （运行时生成）上传图片
└── README.md
```

## API 一览（均返回 `{code, msg, data}`，成功 code=200，未登录 code=401）

| 方法 | 路径 | 鉴权 | 说明 |
| --- | --- | --- | --- |
| POST | `/api/register` | - | JSON `{username, password, phone, student_id}` |
| POST | `/api/login` | - | 返回 `data.token` 及用户信息 |
| GET | `/api/lost/list?page=&per_page=` | - | 失物分页列表 |
| GET | `/api/found/list?page=&per_page=` | - | 拾物分页列表 |
| GET | `/api/lost/{id}` / `/api/found/{id}` | - | 物品详情（含发布者） |
| POST | `/api/lost` / `/api/found` | Bearer | multipart 表单发布（字段含可选 `image` 文件），发布即触发自动匹配 |
| GET | `/api/search?q=` | - | 关键词搜索，返回 `{lost, found}` |
| GET | `/api/match/list` | Bearer | 我的匹配记录（含匹配度、双方物品） |
| POST | `/api/match/{id}/confirm` | Bearer | 确认匹配（双方物品转为已解决） |
| POST | `/api/match/{id}/reject` | Bearer | 忽略匹配 |
| GET | `/api/user/profile` | Bearer | 个人信息与 lost/found/match 计数 |
| GET | `/api/user/items` | Bearer | 我发布的失物与拾物 |

## 遗留说明

- 匹配为启发式规则（类别必须相同，得分 = 0.5 类别 + 0.3 标题/描述二元组相似度 + 0.2 地点相似度，≥0.55 建立匹配），非机器学习模型。
- 服务器重启不会丢失数据（SQLite 落盘）；上传文件仅做扩展名与 5MB 大小校验。
