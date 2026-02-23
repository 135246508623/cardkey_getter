import re
import requests
from .utils import generate_telemetry, generate_fingerprint
from .config import SENTRY_BASE

class CaptchaSolver:
    def solve(self, puzzle_data):
        instruction = puzzle_data["puzzle"]["instruction"].lower()
        shapes = puzzle_data["puzzle"]["shapes"]

        if "largest" in instruction or "smallest" in instruction:
            return self._solve_size_comparison(instruction, shapes)
        elif "find" in instruction:
            return self._solve_find_object(instruction, shapes)
        elif "rotate" in instruction or "align" in instruction:
            return self._solve_rotate(instruction, shapes)
        else:
            raise ValueError(f"未知指令: {instruction}")

    def _solve_size_comparison(self, instruction, shapes):
        match = re.search(r"(largest|smallest) (\w+)", instruction)
        if not match:
            raise ValueError(f"无法解析大小比较指令: {instruction}")
        comparator = match.group(1)
        shape_type = match.group(2)

        candidates = [(i, s) for i, s in enumerate(shapes) if s["type"].lower() == shape_type.lower()]
        if not candidates:
            raise ValueError(f"未找到类型 {shape_type}")

        if comparator == "largest":
            target = max(candidates, key=lambda x: x[1]["size"])
        else:
            target = min(candidates, key=lambda x: x[1]["size"])
        return target[0]

    def _solve_find_object(self, instruction, shapes):
        words = instruction.split()
        target_type = words[-1] if words else ""
        for i, s in enumerate(shapes):
            if s["type"].lower() == target_type.lower():
                return i
        raise ValueError(f"未找到类型 {target_type}")

    def _solve_rotate(self, instruction, shapes):
        if not shapes:
            raise ValueError("没有图形")
        current_orientation = shapes[0].get("orientation", 0)
        required_rotation = (360 - current_orientation) % 360
        return required_rotation

def bypass_captcha(session):
    telemetry = generate_telemetry()
    fingerprint = generate_fingerprint()
    req_payload = {
        "telemetry": telemetry,
        "deviceFingerprint": fingerprint,
        "forcePuzzle": False
    }
    try:
        r = session.post(f"{SENTRY_BASE}/request", json=req_payload, timeout=15)
        r.raise_for_status()
        puzzle_response = r.json()
    except Exception as e:
        raise Exception(f"获取拼图失败: {e}")
    if "puzzle" not in puzzle_response:
        raise Exception("响应中无拼图数据")
    try:
        solver = CaptchaSolver()
        answer = solver.solve(puzzle_response)
    except Exception as e:
        raise Exception(f"解答拼图失败: {e}")
    verify_payload = {
        "id": puzzle_response["id"],
        "answer": answer
    }
    try:
        v = session.post(f"{SENTRY_BASE}/verify", json=verify_payload, timeout=15)
        v.raise_for_status()
        verify_result = v.json()
    except Exception as e:
        raise Exception(f"验证失败: {e}")
    return session
