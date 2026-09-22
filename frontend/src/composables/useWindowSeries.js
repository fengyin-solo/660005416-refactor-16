import { computed } from 'vue';
import { useLogStore } from '../store/log';
/** 模块级单例：同一份接口结果只做一次映射，两个面板共享同一计算缓存 */
let cachedSeries = null;
function buildSeries(windows, anomalies) {
    // 分数只从 anomalies 取一次，按 windowIndex 归到窗口数组下标
    const scoreByIndex = new Map();
    for (const a of anomalies)
        scoreByIndex.set(a.windowIndex, a);
    const points = windows.map((w, index) => {
        const score = scoreByIndex.get(index);
        return {
            index,
            label: 'W' + index,
            count: w.count,
            start: w.start,
            end: w.end,
            sigmaScore: score?.sigmaScore ?? 0,
            iqrScore: score?.iqrScore ?? 0,
            isAnomaly: score?.isAnomaly ?? false,
            timestamp: score?.timestamp ?? ''
        };
    });
    return {
        points,
        labels: points.map(p => p.label),
        counts: points.map(p => p.count),
        sigmaScores: points.map(p => p.sigmaScore),
        iqrScores: points.map(p => p.iqrScore),
        anomalies
    };
}
export function useWindowSeries() {
    if (cachedSeries)
        return cachedSeries;
    const store = useLogStore();
    const series = computed(() => {
        const result = store.result;
        if (!result) {
            return { points: [], labels: [], counts: [], sigmaScores: [], iqrScores: [], anomalies: [] };
        }
        return buildSeries(result.windows, result.anomalies);
    });
    cachedSeries = series;
    return series;
}
