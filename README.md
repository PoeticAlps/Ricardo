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

## 部署

### 方式一：Docker（推荐，一条命令部署到任何机器）

机器上只需有 Docker（含 Compose 插件），无需 Python 环境：

```bash
docker compose up -d --build
```

启动后访问 **http://localhost:8000**。容器每次启动都会先执行一次演示种子脚本
（`backend/seed_demo.py`，幂等：已灌过数据会自动跳过），所以首次打开就能看到
3 个演示账号和 10 条校园失物/拾物数据。

- **数据持久化**：SQLite 数据库与上传图片存放在具名数据卷 `hepu-data`（容器内 `/data`），
  `docker compose down`、重建容器都不会丢数据；彻底清空用 `docker compose down -v`
- **重新灌演示数据**：`docker compose exec hepu python backend/seed_demo.py --reset`
- **查看日志**：`docker compose logs -f`（种子脚本的账号信息也在这里）
- 不用 Compose 时也可：`docker build -t hepu . && docker run -p 8000:8000 hepu`
  （此方式数据仅存于容器内，未挂卷）

### 方式二：本地 venv

```bash
./backend/run.sh               # 自动建 venv、装依赖并启动（监听 127.0.0.1:8000）
python3 backend/seed_demo.py   # （可选）另开一个终端灌入演示数据，随时可跑，幂等
```

### 演示账号

由 `backend/seed_demo.py` 创建，密码统一为 `demo12345`：

| 用户名 | 密码 | 说明 |
| --- | --- | --- |
| demo_alice | demo12345 | 演示用户一（发布了失物与拾物若干） |
| demo_bob | demo12345 | 演示用户二 |
| demo_carol | demo12345 | 演示用户三 |

种子数据共 10 条（失物 5 / 拾物 5），其中校园卡、蓝牙耳机、宿舍钥匙三对为
"同类别 + 相似描述 + 同地点"，会走真实匹配算法自动生成匹配记录（校园卡一对
已确认为"已解决"），其余为待匹配孤品；每条数据附一张纯色占位图。

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
├── Dockerfile              # Docker 镜像（python:3.11-slim + uvicorn）
├── docker-compose.yml      # 一条命令部署，数据卷 hepu-data 持久化
├── .dockerignore           # 排除 venv/ db/ uploads/ 等不入镜像
├── backend/
│   ├── main.py             # FastAPI 应用（API + 静态托管 + 建表）
│   ├── requirements.txt    # fastapi / uvicorn / python-multipart
│   ├── run.sh              # 本地一键启动脚本
│   ├── seed_demo.py        # 演示种子数据脚本（幂等，--reset 重灌）
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
