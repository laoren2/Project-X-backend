from app.core.tools import haversine
from app.schemas.base import BizException
from app.schemas.training.common import (
    Checkpoint, Segment
)
from app.schemas.competition.common import PathPoint
from app.core.errors import ErrorCode
from shapely.geometry import LineString


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