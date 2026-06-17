from app.core.tools import haversine
from app.schemas.base import BizException
from app.schemas.training.common import (
    Checkpoint, Segment
)
from app.schemas.competition.common import PathPoint
from app.core.errors import ErrorCode
from shapely.geometry import LineString
import math


def validate_route_data(route_type: str, route_data: dict):
    if "steps" not in route_data:
        raise BizException(code=ErrorCode.ROUTE_CREATE_FAILED, message="route.data_error.create")

    steps = route_data["steps"]

    if not isinstance(steps, list) or len(steps) < 2:
        raise BizException(code=ErrorCode.ROUTE_CREATE_FAILED, message="route.data_error.create")

    parsed_steps = []
    checkpoints = []
    for step in steps:
        if step["kind"] == "checkpoint":
            cp = Checkpoint(**step)
            parsed_steps.append(cp)
            checkpoints.append(cp)
        elif step["kind"] == "segment":
            parsed_steps.append(Segment(**step))
        else:
            raise BizException(code=ErrorCode.ROUTE_CREATE_FAILED, message="route.data_error.create")

    # 必须以 checkpoint 开始和结束
    if parsed_steps[0].kind != "checkpoint":
        raise BizException(code=ErrorCode.ROUTE_CREATE_FAILED, message="route.data_error.create")

    if parsed_steps[-1].kind != "checkpoint":
        raise BizException(code=ErrorCode.ROUTE_CREATE_FAILED, message="route.data_error.create")

    # route_type 约束
    if route_type == "pointToPoint":
        if len(parsed_steps) != 2:
            raise BizException(code=ErrorCode.ROUTE_CREATE_FAILED, message="route.data_error.create")

    if route_type == "multiPoints":
        if any(s.kind != "checkpoint" for s in parsed_steps):
            raise BizException(code=ErrorCode.ROUTE_CREATE_FAILED, message="route.data_error.create")

    if len(parsed_steps) < 2 or len(checkpoints) > 100:
        raise BizException(code=ErrorCode.ROUTE_CREATE_FAILED, message="route.data_error.create")

    # 校验检查点的覆盖情况:
    for i in range(len(checkpoints)):
        for j in range(i + 1, len(checkpoints)):
            p1 = checkpoints[i]
            p2 = checkpoints[j]
            distance = haversine(
                p1.lat, p1.lng,
                p2.lat, p2.lng
            )
            min_allowed = p1.radius + p2.radius + 10
            if distance <= min_allowed:
                raise BizException(code=ErrorCode.ROUTE_CREATE_FAILED, message="route.data_error.create")

    return parsed_steps

def build_geometry(parsed_steps):
    coords = []
    for step in parsed_steps:
        if step.kind == "checkpoint":
            coords.append((step.lng, step.lat))
        elif step.kind == "segment":
            coords.extend([(lng, lat) for lat, lng in step.points])
    if len(coords) < 2:
        raise BizException(code=ErrorCode.ROUTE_CREATE_FAILED, message="route.data_error.create")
    return LineString(coords)

def extract_path_points(parsed_steps):
    """
    将 steps 转换为可用于 compute_distance 的点序列（List[LocationPoint-like]）
    """
    class _Point:
        def __init__(self, lat: float, lon: float):
            self.lat = lat
            self.lon = lon

    points = []

    for step in parsed_steps:
        if step.kind == "checkpoint":
            points.append(_Point(step.lat, step.lng))
        elif step.kind == "segment":
            for lat, lng in step.points:
                points.append(_Point(lat, lng))

    # 去重连续重复点（避免 checkpoint 和 segment 连接处重复）
    deduped = []
    prev = None
    for p in points:
        if prev is None or (p.lat != prev.lat or p.lon != prev.lon):
            deduped.append(p)
        prev = p

    return deduped


def extract_checkpoints_from_route_data(route_data: dict | None) -> list[dict]:
    """从 route_data.steps 中按顺序提取 checkpoint（含可选 penalty，单位：秒）。"""

    if not route_data or not isinstance(route_data.get("steps"), list):
        return []
    out: list[dict] = []
    for step in route_data["steps"]:
        if not isinstance(step, dict) or step.get("kind") != "checkpoint":
            continue
        try:
            lat = float(step["lat"])
            lng = float(step["lng"])
            radius = float(step["radius"])
        except (KeyError, TypeError, ValueError):
            return []
        raw_pen = step.get("penalty")
        penalty: float | None
        if raw_pen is None or raw_pen == "":
            penalty = None
        else:
            try:
                penalty = max(0, float(raw_pen))
            except (TypeError, ValueError):
                penalty = None
        out.append({"lat": lat, "lng": lng, "radius": radius, "penalty": penalty})
    return out


def _inside_checkpoint(lat: float, lon: float, cp: dict) -> bool:
    # 3m buffer
    return haversine(lat, lon, cp["lat"], cp["lng"]) <= (cp["radius"] + 3.0)


def evaluate_route_training_checkpoint_path(
    path: list[PathPoint],
    checkpoints: list[dict],
) -> tuple[float, bool]:
    """
    校验轨迹是否经过首、尾检查点；按时间顺序统计中间检查点的罚时（秒）。
    若先进入较后检查点再进入较前的检查点，则对跳过的中间点按 penalty 累计（与「完全未经过」在末尾补罚一致）。
    """
    n = len(checkpoints)
    if n < 2 or not path:
        return 0.0, False

    total_penalty = 0.0
    visited = [False] * n
    penalized = [False] * n
    next_expected = 0

    def add_middle_penalty(j: int) -> None:
        nonlocal total_penalty
        if not (1 <= j <= n - 2):
            return
        if penalized[j]:
            return
        p = checkpoints[j].get("penalty")
        if p is None:
            return
        penalized[j] = True
        total_penalty += p

    def on_first_enter(k: int) -> None:
        nonlocal next_expected
        if visited[k]:
            return
        visited[k] = True
        if k > next_expected:
            for j in range(next_expected, k):
                add_middle_penalty(j)
            next_expected = k + 1
        elif k == next_expected:
            next_expected = k + 1

    was_inside = [_inside_checkpoint(path[0].lat, path[0].lon, checkpoints[k]) for k in range(n)]
    for k in range(n):
        if was_inside[k]:
            on_first_enter(k)

    for i in range(1, len(path)):
        lat, lon = path[i].lat, path[i].lon
        entered_here: list[int] = []
        for k in range(n):
            now = _inside_checkpoint(lat, lon, checkpoints[k])
            if now and not was_inside[k]:
                entered_here.append(k)
            was_inside[k] = now
        for k in sorted(entered_here):
            on_first_enter(k)

    for j in range(1, n - 1):
        if not visited[j] and not penalized[j]:
            add_middle_penalty(j)

    passes = visited[0] and visited[n - 1]
    return total_penalty, passes


# ============================================================================
# Split profile：把最佳成绩轨迹处理成「沿路里程 → 有效用时」的定长曲线，
# 供运动中实时预测名次 / 自我对比使用。详见 plan。
# ============================================================================

def _route_vertices(route_data: dict | None) -> list[tuple[float, float]]:
    """从 route_data.steps 取出有序的 (lat, lon) 折线顶点（checkpoints + segment 点），去重相邻重复点。"""
    out: list[tuple[float, float]] = []
    steps = route_data.get("steps") if route_data else None
    if not isinstance(steps, list):
        return out
    for step in steps:
        if not isinstance(step, dict):
            continue
        kind = step.get("kind")
        try:
            if kind == "checkpoint":
                out.append((float(step["lat"]), float(step["lng"])))
            elif kind == "segment":
                for pt in step.get("points", []):
                    out.append((float(pt[0]), float(pt[1])))   # points: [lat, lng]
        except (KeyError, TypeError, ValueError, IndexError):
            continue
    deduped: list[tuple[float, float]] = []
    for v in out:
        if not deduped or deduped[-1] != v:
            deduped.append(v)
    return deduped


def _cumulative_arc_lengths(vertices: list[tuple[float, float]]) -> list[float]:
    """每个顶点处的累计弧长（米），S[-1] = 路线总长 L。"""
    s = [0.0]
    for i in range(1, len(vertices)):
        s.append(s[-1] + haversine(vertices[i - 1][0], vertices[i - 1][1], vertices[i][0], vertices[i][1]))
    return s


def _to_local_xy(lat: float, lon: float, lat0: float, lon0: float) -> tuple[float, float]:
    """以 (lat0, lon0) 为原点的等距矩形近似平面坐标（米）。"""
    m_per_deg_lat = 111320.0
    m_per_deg_lon = 111320.0 * math.cos(math.radians(lat0))
    return ((lon - lon0) * m_per_deg_lon, (lat - lat0) * m_per_deg_lat)


def _project_arc(lat: float, lon: float,
                 vertices: list[tuple[float, float]], cum_s: list[float],
                 d_prev: float, back: float = 30.0, ahead: float = 500.0) -> float:
    """把点投到折线上垂距最近的段，返回沿路弧长（米）。带单调前进窗口，处理来回绕 / 环线。"""
    lo, hi = d_prev - back, d_prev + ahead
    best_perp = float("inf")
    best_arc = d_prev
    for k in range(len(vertices) - 1):
        sa, sb = cum_s[k], cum_s[k + 1]
        if sb < lo or sa > hi:          # 段不在前进窗口内，跳过（解决来回绕歧义）
            continue
        ax, ay = _to_local_xy(vertices[k][0], vertices[k][1], lat, lon)
        bx, by = _to_local_xy(vertices[k + 1][0], vertices[k + 1][1], lat, lon)
        dx, dy = bx - ax, by - ay
        seg2 = dx * dx + dy * dy
        t = 0.0 if seg2 <= 1e-9 else max(0.0, min(1.0, (-ax * dx - ay * dy) / seg2))
        px, py = ax + t * dx, ay + t * dy
        perp = math.hypot(px, py)        # 点在原点，垂距 = |proj|
        if perp < best_perp:
            best_perp = perp
            best_arc = sa + t * (sb - sa)
    return max(best_arc, d_prev)         # 单调不回退


def dynamic_profile_n(length_m: float, sport: str) -> int:
    """里程桩数量 N，按运动类型 + 路线距离动态。"""
    km = length_m / 1000.0
    if sport == "bike":
        if km < 1:
            return 5
        if km > 20:
            return 100
        return round(5 + (km - 1) / 19.0 * 95)
    # running 及其他
    if km < 1:
        return 10
    if km > 10:
        return 100
    return round(10 + (km - 1) / 9.0 * 90)


def _resample(samples: list[tuple[float, float]], length: float, n: int) -> list[float]:
    """在 d_i = i*L/N 上对 (d, t) 分段线性重采样，得 N+1 个有效用时。"""
    splits: list[float] = []
    j = 0
    for i in range(n + 1):
        di = length * i / n
        while j + 1 < len(samples) and samples[j + 1][0] < di:
            j += 1
        if j + 1 >= len(samples):
            splits.append(samples[-1][1])
            continue
        d0, t0 = samples[j]
        d1, t1 = samples[j + 1]
        if d1 <= d0:
            splits.append(t0)
        else:
            r = max(0.0, min(1.0, (di - d0) / (d1 - d0)))
            splits.append(t0 + r * (t1 - t0))
    return splits


def build_split_profile(base_points: list[PathPoint], route_data: dict | None,
                        effective_total: float, sport: str) -> dict | None:
    """
    把最佳成绩的完整轨迹处理成 {L, N, splits} 的 split profile。
    - base_points: 轨迹基础点（含 lat/lon/timestamp），取自 [p.base for p in info.path]
    - effective_total: 该记录的有效完赛时间（= 排行榜用的 duration_seconds）
    - sport: "bike" / "running"，决定动态 N
    每个点的经过时刻按「有效时间」线性折算（k = 有效/原始），使端点 splits[N] == effective_total。
    """
    if not base_points or len(base_points) < 2:
        return None
    vertices = _route_vertices(route_data)
    if len(vertices) < 2:
        return None
    cum_s = _cumulative_arc_lengths(vertices)
    length = cum_s[-1]
    if length <= 0:
        return None
    start_ts = base_points[0].timestamp
    raw_total = base_points[-1].timestamp - start_ts
    if raw_total <= 0:
        return None
    k = effective_total / raw_total

    samples: list[tuple[float, float]] = []
    d_prev = 0.0
    for p in base_points:
        d_prev = _project_arc(p.lat, p.lon, vertices, cum_s, d_prev)
        samples.append((d_prev, (p.timestamp - start_ts) * k))

    n = dynamic_profile_n(length, sport)
    splits = _resample(samples, length, n)
    return {"L": length, "N": n, "splits": splits}