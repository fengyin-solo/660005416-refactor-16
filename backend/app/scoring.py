"""共享的窗口聚合与异常分数口径。

异常分数面板与窗口日志量面板（以及告警生成）都必须从本模块的同一份
窗口记录取值，避免两处各写一套 3-sigma / IQR 计算导致分数不一致。

分数在本模块只计算一次：`window_score_records` 返回的每条记录同时携带
窗口事实（start/end/count）与分数（sigmaScore/iqrScore/isAnomaly），
接口层只做字段投影，不再做第二次分数映射。
"""
from collections import Counter

import numpy as np

# 演示用固定窗口大小（每条窗口 20 条日志）
WINDOW_SIZE = 20

# 异常判定阈值
SIGMA_LIMIT = 2.5
IQR_LIMIT = 3.0
IQR_SCORE_CAP = 10.0

# anomalies 接口字段 / windows 接口字段（投影用，保持原有字段名）
ANOMALY_FIELDS = ("windowIndex", "sigmaScore", "iqrScore", "isAnomaly", "timestamp")
WINDOW_FIELDS = ("start", "end", "count", "levels", "sources")


def build_windows(logs, window_size=WINDOW_SIZE):
    """按日志下标切分窗口并聚合级别/来源，窗口下标即数组下标。"""
    windows = []
    n = len(logs)
    for i in range(0, n, window_size):
        chunk = logs[i:i + window_size]
        windows.append({
            "start": i,
            "end": min(i + window_size, n),
            "count": len(chunk),
            "levels": dict(Counter(l["level"] for l in chunk)),
            "sources": dict(Counter(l["source"] for l in chunk)),
        })
    return windows


def score_windows(windows, logs, window_size=WINDOW_SIZE):
    """对窗口列表计算一次 3-sigma / IQR 分数与异常判定。

    返回与 windows 一一对应的记录列表（同一数组下标即窗口序号），
    每条记录是窗口事实 + 分数的唯一来源。
    """
    counts = [w["count"] for w in windows]

    mean = float(np.mean(counts))
    std = float(np.std(counts)) if len(counts) > 1 else 1.0
    q1 = float(np.percentile(counts, 25)) if len(counts) > 3 else mean - std
    q3 = float(np.percentile(counts, 75)) if len(counts) > 3 else mean + std
    iqr = q3 - q1 if q3 > q1 else 1.0

    iqr_low = q1 - 1.5 * iqr
    iqr_high = q3 + 1.5 * iqr

    records = []
    for i, w in enumerate(windows):
        sigma_score = abs(w["count"] - mean) / max(std, 1e-5)
        iqr_score = 0.0
        if w["count"] < iqr_low or w["count"] > iqr_high:
            iqr_score = min(IQR_SCORE_CAP, abs(w["count"] - mean) / max(iqr, 1e-5))
        records.append({
            "windowIndex": i,
            "start": w["start"],
            "end": w["end"],
            "count": w["count"],
            "sigmaScore": round(sigma_score, 2),
            "iqrScore": round(iqr_score, 2),
            "isAnomaly": sigma_score > SIGMA_LIMIT or iqr_score > IQR_LIMIT,
            "timestamp": logs[i * window_size]["timestamp"] if i * window_size < len(logs) else "",
        })
    return records


def window_score_records(logs, window_size=WINDOW_SIZE):
    """共用入口：一次产出窗口聚合与对应分数记录（空日志返回两个空列表）。"""
    windows = build_windows(logs, window_size)
    if not windows:
        return windows, []
    return windows, score_windows(windows, logs, window_size)


def project_fields(records, fields):
    """按原有字段名投影，分数不在此处重复计算。"""
    return [{k: r[k] for k in fields} for r in records]
