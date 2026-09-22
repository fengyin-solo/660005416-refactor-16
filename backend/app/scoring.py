"""共用的窗口聚合与异常分数实现。

异常分数面板与窗口日志量面板都从本模块的同一份结果取值：
- 窗口序号一律按窗口数组下标 (enumerate) 生成，不再由日志条数推算；
- 3-sigma / IQR 两套分数与判定只在此处计算一遍。

数值口径与历史实现保持一致（NumPy 默认：总体标准差 ddof=0、
百分位线性插值），字段名保持不变。
"""
from collections import Counter

import numpy as np

WINDOW_SIZE = 20

# 判定阈值（沿用原有口径）
SIGMA_ANOMALY_THRESHOLD = 2.5
IQR_ANOMALY_THRESHOLD = 3.0
IQR_SCORE_CAP = 10.0


def build_windows(logs, window_size=WINDOW_SIZE):
    """按固定条数切分日志，返回窗口列表（字段与历史响应一致）。"""
    windows = []
    for start in range(0, len(logs), window_size):
        chunk = logs[start:start + window_size]
        windows.append({
            "start": start,
            "end": min(start + window_size, len(logs)),
            "count": len(chunk),
            "levels": dict(Counter(l["level"] for l in chunk)),
            "sources": dict(Counter(l["source"] for l in chunk)),
        })
    return windows


def score_windows(windows, logs, window_size=WINDOW_SIZE):
    """对一组窗口计算 3-sigma / IQR 分数及异常判定（只算一遍）。

    返回与窗口数组一一对应的列表，窗口序号即数组下标。
    """
    counts = [w["count"] for w in windows]
    mean = float(np.mean(counts))
    std = float(np.std(counts)) if len(counts) > 1 else 1.0
    q1 = float(np.percentile(counts, 25)) if len(counts) > 3 else mean - std
    q3 = float(np.percentile(counts, 75)) if len(counts) > 3 else mean + std
    iqr = q3 - q1 if q3 > q1 else 1.0

    scored = []
    for index, w in enumerate(windows):
        sigma_score = abs(w["count"] - mean) / max(std, 1e-5)
        iqr_low = q1 - 1.5 * iqr
        iqr_high = q3 + 1.5 * iqr
        iqr_score = 0.0
        if w["count"] < iqr_low or w["count"] > iqr_high:
            iqr_score = min(IQR_SCORE_CAP, abs(w["count"] - mean) / max(iqr, 1e-5))
        log_offset = index * window_size
        scored.append({
            "windowIndex": index,
            "sigmaScore": round(sigma_score, 2),
            "iqrScore": round(iqr_score, 2),
            "isAnomaly": sigma_score > SIGMA_ANOMALY_THRESHOLD
                         or iqr_score > IQR_ANOMALY_THRESHOLD,
            "timestamp": logs[log_offset]["timestamp"] if log_offset < len(logs) else "",
        })
    return scored
