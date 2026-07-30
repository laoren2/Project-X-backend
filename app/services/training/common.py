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
    结算与水印必须使用同一状态机，避免同一条轨迹在两处得到不同罚时。
    """
    _, total_penalty, passes = build_route_checkpoint_events(path, checkpoints)
    return total_penalty, passes


def build_route_checkpoint_events(
    path: list[PathPoint],
    checkpoints: list[dict],
) -> tuple[list[dict], float, bool]:
    """重放检查点状态机，产出可供实时回放使用的罚时事件。

    事件发生在首次进入某个后续检查点的轨迹点：此前尚未经过的中间点会
    同时标记为 miss，并在这一刻累加其罚时。这个顺序与结算校验保持一致，
    使视频水印的有效用时不会在终点才突然补上全部罚时。
    """
    n = len(checkpoints)
    if n < 2 or not path:
        return [], 0.0, False

    events: list[dict] = []
    visited = [False] * n
    penalized = [False] * n
    next_expected = 0
    cumulative_penalty = 0.0

    def enter(k: int, timestamp: float) -> None:
        nonlocal next_expected, cumulative_penalty
        if visited[k]:
            return
        advances_stage = k >= next_expected
        missed_indices: list[int] = []
        penalty_delta = 0.0
        if k > next_expected:
            for j in range(next_expected, k):
                if not (1 <= j <= n - 2) or penalized[j]:
                    continue
                penalized[j] = True
                missed_indices.append(j)
                penalty_delta += checkpoints[j].get("penalty") or 0.0
        visited[k] = True
        next_expected = max(next_expected, k + 1)
        cumulative_penalty += penalty_delta
        # 起点仅初始化阶段；后续经过点（即使罚时为 0）也要记录，以便回放时切段。
        if k > 0 and advances_stage:
            events.append({
                "timestamp": float(timestamp),
                "checkpoint_index": k,
                "missed_checkpoint_indices": missed_indices,
                "penalty_delta": penalty_delta,
                "cumulative_penalty": cumulative_penalty,
            })

    was_inside = [_inside_checkpoint(path[0].lat, path[0].lon, checkpoints[k]) for k in range(n)]
    for k, inside in enumerate(was_inside):
        if inside:
            enter(k, path[0].timestamp)

    for i in range(1, len(path)):
        entered_here: list[int] = []
        for k in range(n):
            now = _inside_checkpoint(path[i].lat, path[i].lon, checkpoints[k])
            if now and not was_inside[k]:
                entered_here.append(k)
            was_inside[k] = now
        for k in sorted(entered_here):
            enter(k, path[i].timestamp)

    # 对未经过的中间点保持与结算完全一致的兜底。有效路线必定经过终点，
    # 因此正常情况下这些罚时都会在进入终点的事件中产生。
    for j in range(1, n - 1):
        if not visited[j] and not penalized[j]:
            penalized[j] = True
            cumulative_penalty += checkpoints[j].get("penalty") or 0.0

    return events, cumulative_penalty, visited[0] and visited[n - 1]


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


def _project_segment_progress(lat: float, lon: float,
                              start: tuple[float, float], end: tuple[float, float]) -> float:
    """将点投影到单个检查点段，返回该段内 [0, 1] 的规范进度。"""
    ax, ay = _to_local_xy(start[0], start[1], lat, lon)
    bx, by = _to_local_xy(end[0], end[1], lat, lon)
    dx, dy = bx - ax, by - ay
    seg2 = dx * dx + dy * dy
    if seg2 <= 1e-9:
        return 0.0
    return max(0.0, min(1.0, (-ax * dx - ay * dy) / seg2))


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
    # 终点可能有多个相同规范进度的采样（进入终点后仍会记录一帧）。
    # 保持 PB 曲线的终点严格等于结算有效成绩，不能落在第一帧进入终点的时刻。
    if splits:
        splits[-1] = samples[-1][1]
    return splits


def build_split_profile(base_points: list[PathPoint], route_data: dict | None,
                        effective_total: float, sport: str,
                        checkpoint_events: list[dict] | None = None,
                        card_bonus_samples: list[tuple[float, float]] | None = None,
                        original_duration_seconds: float | None = None) -> dict | None:
    """
    把最佳成绩的完整轨迹处理成 {L, N, splits} 的 split profile。
    - base_points: 轨迹基础点（含 lat/lon/timestamp），取自 [p.base for p in info.path]
    - effective_total: 该记录的有效完赛时间（= 排行榜用的 duration_seconds）
    - sport: "bike" / "running"，决定动态 N
    每个点的经过时刻按「有效时间」线性折算（k = 有效/原始），使端点 splits[N] == effective_total。
    """
    if not base_points or len(base_points) < 2:
        return None
    checkpoints = extract_checkpoints_from_route_data(route_data)
    if len(checkpoints) < 2:
        return None
    # 比赛等旧调用方未显式传事件时，在服务端用同一条轨迹即时重放，避免退回
    # 到跨未来段的全局投影算法。
    if checkpoint_events is None:
        checkpoint_events, _, _ = build_route_checkpoint_events(base_points, checkpoints)
    vertices = [(cp["lat"], cp["lng"]) for cp in checkpoints]
    cum_s = _cumulative_arc_lengths(vertices)
    length = cum_s[-1]
    if length <= 0:
        return None
    start_ts = base_points[0].timestamp
    path_duration = base_points[-1].timestamp - start_ts
    raw_total = original_duration_seconds if original_duration_seconds is not None else path_duration
    if raw_total <= 0 or path_duration <= 0:
        return None
    path_time_scale = raw_total / path_duration
    event_penalty_total = (checkpoint_events or [])[-1]["cumulative_penalty"] if checkpoint_events else 0.0
    raw_card_total = card_bonus_samples[-1][1] if card_bonus_samples else 0.0
    # 卡牌在结算时可能被 20% 上限截断。按最终实际生效比例回放每个时刻的累计减时。
    applied_card_total = max(0.0, raw_total + event_penalty_total - effective_total)
    card_scale = min(1.0, applied_card_total / raw_card_total) if raw_card_total > 0 else 0.0

    def penalty_at(timestamp: float) -> float:
        penalty = 0.0
        for event in checkpoint_events or []:
            if event["timestamp"] > timestamp:
                break
            penalty = event["cumulative_penalty"]
        return penalty

    def card_bonus_at(index: int) -> float:
        if not card_bonus_samples:
            return 0.0
        # 路径点和累计卡牌快照同序；缺失数据时采用最后一个已知值。
        return card_bonus_samples[min(index, len(card_bonus_samples) - 1)][1] * card_scale

    # 规范进度只能在当前检查点段内前进。绝不能从全局折线寻找最近段：
    # 环线/折返时那会把位置错误吸附到未来段，造成 PB 和 rank 的突跳。
    events = sorted(checkpoint_events or [], key=lambda event: event["timestamp"])
    event_index = 0
    active_checkpoint = 0
    local_progress = 0.0
    samples: list[tuple[float, float]] = []
    for point_index, p in enumerate(base_points):
        advanced_checkpoint = False
        while event_index < len(events) and events[event_index]["timestamp"] <= p.timestamp:
            advanced_checkpoint = advanced_checkpoint or int(events[event_index]["checkpoint_index"]) > active_checkpoint
            active_checkpoint = max(active_checkpoint, int(events[event_index]["checkpoint_index"]))
            local_progress = 0.0
            event_index += 1
        if active_checkpoint >= len(vertices) - 1:
            d = length
        else:
            segment_length = cum_s[active_checkpoint + 1] - cum_s[active_checkpoint]
            projected = _project_segment_progress(
                p.lat, p.lon, vertices[active_checkpoint], vertices[active_checkpoint + 1]
            )
            if point_index > 0 and not advanced_checkpoint:
                delta_seconds = max(0.0, p.timestamp - base_points[point_index - 1].timestamp)
                max_speed = 10.0 if sport == "running" else 25.0
                max_advance = max(30.0, max_speed * delta_seconds) / max(segment_length, 1.0)
                projected = min(projected, local_progress + max_advance)
            # 仅在本段内保持单调，避免定位噪声使显示来回抖动。
            local_progress = max(local_progress, projected)
            d = cum_s[active_checkpoint] + local_progress * segment_length
        effective_time = max(0.0, (p.timestamp - start_ts) * path_time_scale - card_bonus_at(point_index) + penalty_at(p.timestamp))
        samples.append((d, effective_time))

    # 防御性收口：历史数据可能缺少逐点卡牌快照，仍保证 profile 终点与排行榜成绩一致。
    if samples and samples[-1][1] != effective_total:
        correction = effective_total - samples[-1][1]
        samples = [(d, max(0.0, t + correction * (t / samples[-1][1] if samples[-1][1] > 0 else 1.0))) for d, t in samples]

    n = dynamic_profile_n(length, sport)
    splits = _resample(samples, length, n)
    return {"L": length, "N": n, "splits": splits}
