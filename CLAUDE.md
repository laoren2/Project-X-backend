# CLAUDE.md

Guidance for Claude Code (and humans) working in this repository.

## What this is

SportsX 运动 App 后端 —— FastAPI 用户中心 / 比赛 / 训练服务。提供 App 客户端 API（`/api/v1`）与运营管理后台 API（`/api/internal`）。

**技术栈**：Python · FastAPI · SQLAlchemy 2.0 (async) · PostgreSQL 15 + PostGIS · Redis 7 · Alembic · APScheduler · Docker。第三方：阿里云 OCR/短信/OSS/邮件、Apple IAP、GeoIP2。

## Architecture

分层架构，请求自上而下流经：

```
API (app/api)  →  Service (app/services)  →  CRUD/Repository (app/crud)  →  Model/DB (app/db/models)
                         ↓                            ↓
                   Redis / 第三方 SDK            AsyncSession (asyncpg)
```

层次职责（**改代码时请遵守，不要跨层**）：

- **API 层** `app/api/` — 路由、依赖注入、请求/响应校验。不写业务逻辑，调用 service。
  - `v1/` 客户端接口（`get_current_user` 鉴权）；`internal/` 管理后台（`get_current_admin`，需 admin role）。
  - 子域按业务划分，competition/training 再按运动类型拆 `bike.py` / `running.py`。
- **Service 层** `app/services/` — **全部业务逻辑在此**。持有 `AsyncSession` 并管理事务（commit），直接操作 Redis 和第三方 SDK。最厚的一层。
- **CRUD/Repository 层** `app/crud/` — 纯数据访问，函数式风格：`async def fn(db: AsyncSession, ...) -> ORM`。只做 SQLAlchemy 查询，**不含业务判断、不 commit**。
- **Model 层** `app/db/models/` — SQLAlchemy ORM（`declarative_base`）。
- **Schema 层** `app/schemas/` — Pydantic 请求/响应模型 + i18n。
- **Core** `app/core/` — config、security、errors、storage、logging、tools 等横切关注点。

入口：[app/main.py](app/main.py) —— `lifespan` 中测试 Redis/DB 连接、启动 APScheduler；挂载两套 router 与 `/resources` 静态目录；注册 `BizException` 全局异常处理器。

## Key conventions

- **统一响应封装**：所有接口返回 `BaseResponse[T]`（[app/schemas/base.py](app/schemas/base.py)），字段 `access_token / code / message / data`。
- **统一业务异常**：抛 `BizException(code=ErrorCode.X, message="i18n.key", params={...})`，不要直接抛 HTTP 错误。错误码与多语言文案集中在 [app/core/errors.py](app/core/errors.py)（`ErrorCode` + `ERROR_MESSAGES`）。
- **i18n**：语言由 `Accept-Language` 头解析（`get_language` in [app/api/deps.py](app/api/deps.py)），支持 `zh-Hans / zh-Hant / en / ko / ja`，默认 `en`。DB 中多语言文本用 `JSONB` 字段（命名 `*_i18n`），渲染走 `pick_i18n_text`。
- **鉴权 / Token**：自有 JWT（HS256，[app/core/security.py](app/core/security.py)）。Token 剩余 <7 天时自动续期，新 token 经 `AuthContext.new_token` 下发。封禁用户在 `get_current_user` 中处理（含到期自动解封）。
- **主键约定**：表用 UUID 主键 + 业务字符串 ID（如 `user_id` / `event_id` / `region_id`，唯一索引）。
- **关系声明**：模型间用显式 `primaryjoin="...foreign(...)..."`，**非数据库外键约束**。
- **全异步**：DB（asyncpg）、Redis（redis.asyncio）、HTTP（httpx）均为 async。阻塞调用（如 SMTP）须放线程池，勿阻塞 event loop（见 `_send_smtp` 的用法）。

## Redis usage

连接池在 [app/db/session.py](app/db/session.py)（`redis_client`）。三类用途：

1. **比赛实时排行榜**（核心，`app/services/competition/`）：`ZSET` key `leaderboard:{sport}:{track_id}:{male|female}`；定时 `ZUNIONSTORE` 生成带时间戳快照 `...:snapshot:{ts}`（TTL 300s），快照上算名次/奖励写入 `HASH` `...:rewards`（TTL 360s）。
2. **短信验证码 / 限流**（`app/services/sms.py`）：`sms:{phone}`、`sms:rate:{phone}`。
3. **用户层缓存**（`app/services/user.py`）：邮箱验证码等。

修改排行榜逻辑时注意 Redis key 拼接散落在 `competition/{common,bike,running}.py`，三处需保持一致。

## Scheduled tasks

APScheduler，定义在 [app/scheduler/task.py](app/scheduler/task.py)，随 app lifespan 启停：

- 每 **1 分钟**：生成各赛道排行榜快照。
- 每 **1 小时**：清理过期比赛记录 / 过期组队。

每个任务自建 `AsyncSessionLocal()` 会话。

## Third-party integrations

| 集成 | 位置 |
|---|---|
| 阿里云 OCR（实名认证证件识别 HK/TW/KR/US） | `app/services/user.py` |
| 阿里云短信 | `app/services/sms.py` |
| 阿里云 OSS（资源上传，按 ENV 分 bucket） | `app/services/common.py` |
| 阿里云邮件（SMTP_SSL 465） | `app/services/user.py` |
| Apple IAP / App Store（订阅查询、交易验签，prod/sandbox 双 client） | `app/services/iap.py`、`app/services/app_store_api_tool.py` |
| GeoIP2（IP 归属国家） | `app/api/v1/common.py` |
| 地理空间（PostGIS / geoalchemy2 / shapely / SRTM 海拔） | models、`app/services/common.py` |

## Database & migrations

- PostgreSQL 15 + **PostGIS**（`regions.boundary` 用 `Geometry(MULTIPOLYGON, srid=4326)`）。
- 迁移用 Alembic（`alembic/versions/`，[alembic/env.py](alembic/env.py) 导入 `Base.metadata` 全量自动生成）。
- **改了 `app/db/models/` 后**：`alembic revision --autogenerate -m "..."` 生成迁移，再 `alembic upgrade head`。新增 model 文件需确保被 `app/db/models/__init__.py` 导入，否则 autogenerate 不识别。

## Dev workflow

```bash
# 本地起全套（含 db + redis + backend，backend 本地用 certs 启 SSL）
docker compose up

# 仅依赖，本机跑 app：
docker compose up -d db redis
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

- 配置通过根目录 `.env`（模板见 `.env.example`）。设置项定义在 [app/core/config.py](app/core/config.py)（`Settings`）。
- **机密文件勿动 / 勿读**：`.env`、`certs/`（证书密钥），已在 `.gitignore` / `.dockerignore` 中排除。

## Deployment (CI/CD)

GitHub Actions（`.github/workflows/`）：构建推送镜像 → SSH 到服务器拉取 → `alembic upgrade head` → 重启 backend + Caddy。

- **Dev** [deploy-dev.yml](.github/workflows/deploy-dev.yml)：`push` 到 `main` 触发，镜像 tag `dev-latest`，部署 `/opt/sporreer_dev`。
- **Prod** [deploy-prod.yml](.github/workflows/deploy-prod.yml)：`push` tag `v*.*.*` 触发，镜像双 tag `latest` + 版本号，部署 `/opt/sporreer_prod`。

注意：服务器侧 `docker-compose.yml`（含 Caddy）位于 `/opt/sporreer_*`，不在本仓库。

## Gotchas

- 命名混用：仓库 `sportsX_backend`、本地镜像 `sportsx_backend`，但 CI 镜像 / CDN 域名用 `sporreer_backend` / `valbara.top`。改部署相关内容时注意区分，勿"顺手纠正"。
- Service 层既管事务又拼 Redis key，耦合较高；新增比赛/排行榜逻辑前先读懂 `competition/common.py`。
- `git` 提交信息以英文 `[feature]/[bugfix]/[optimize]` 前缀（见 git log），PR 合并到 `main`。
- 产品的命名已经正式更新为 Movmov，遗留的一些变量和文件命名（如sportsx/sporreer）不需要更新，但是涉及到的新需求需要注意使用最新名称。
