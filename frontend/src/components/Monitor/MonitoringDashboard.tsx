import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Activity, Cpu, HardDrive, Server, AlertTriangle, Clock, Zap,
  TrendingUp, RefreshCw, Loader2, ChevronDown, ChevronUp,
} from 'lucide-react';
import { monitoringApi, type DashboardData } from '@/services/api';

function formatBytes(mb: number): string {
  if (mb < 1024) return `${mb.toFixed(0)} MB`;
  return `${(mb / 1024).toFixed(1)} GB`;
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 24) return `${Math.floor(h / 24)}d ${h % 24}h`;
  return `${h}h ${m}m`;
}

function ScoreRing({ score, label }: { score: number; label: string }) {
  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const scoreColor = score >= 80 ? '#22c55e' : score >= 50 ? '#eab308' : '#ef4444';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, minWidth: 100 }}>
      <svg width="84" height="84" viewBox="0 0 84 84">
        <circle cx="42" cy="42" r={radius} fill="none" stroke="var(--hairline)" strokeWidth="6" />
        <circle
          cx="42" cy="42" r={radius} fill="none"
          stroke={scoreColor} strokeWidth="6"
          strokeDasharray={circumference} strokeDashoffset={offset}
          strokeLinecap="round" transform="rotate(-90 42 42)"
          style={{ transition: 'stroke-dashoffset 0.6s ease' }}
        />
        <text x="42" y="42" textAnchor="middle" dominantBaseline="central"
          style={{ fontSize: 18, fontWeight: 700, fill: scoreColor }}>{score.toFixed(0)}</text>
      </svg>
      <span style={{ fontSize: 11, color: 'var(--mute)', textAlign: 'center' }}>{label}</span>
    </div>
  );
}

function MiniBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div style={{ height: 6, borderRadius: 3, background: 'var(--hairline)', overflow: 'hidden' }}>
      <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 3, transition: 'width 0.4s ease' }} />
    </div>
  );
}

export const MonitoringDashboard: React.FC = () => {
  const { t } = useTranslation();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedSection, setExpandedSection] = useState<string | null>('health');

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await monitoringApi.getDashboard();
      setData(res.data ?? null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
    const interval = setInterval(loadDashboard, 30000);
    return () => clearInterval(interval);
  }, [loadDashboard]);

  const health = data?.health;
  const requests = data?.requests;
  const system = data?.system;
  const webVitals = data?.web_vitals;

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', color: 'var(--ink)', overflow: 'auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 16px', borderBottom: '1px solid var(--hairline)' }}>
        <Activity size={16} style={{ color: 'var(--accent)' }} />
        <span style={{ fontWeight: 600, fontSize: 14 }}>{t('monitoring.title', '性能监控')}</span>
        <button
          onClick={loadDashboard}
          disabled={loading}
          style={{ marginLeft: 'auto', padding: '4px 8px', borderRadius: 6, border: '1px solid var(--hairline)', background: 'transparent', color: 'var(--mute)', cursor: loading ? 'wait' : 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}
        >
          <RefreshCw size={10} className={loading ? 'animate-spin' : ''} />
          {t('monitoring.refresh', '刷新')}
        </button>
      </div>

      {error && (
        <div style={{ padding: '8px 16px', background: 'rgba(239,68,68,0.1)', color: '#ef4444', fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
          <AlertTriangle size={12} />{error}
        </div>
      )}

      {loading && !data ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 32, gap: 8 }}>
          <Loader2 size={16} className="animate-spin" />
          <span style={{ fontSize: 13, color: 'var(--mute)' }}>{t('monitoring.loading', '加载中...')}</span>
        </div>
      ) : data ? (
        <div style={{ flex: 1, overflow: 'auto' }}>
          {/* Health Score */}
          <div style={{ borderBottom: '1px solid var(--hairline)' }}>
            <div onClick={() => toggleSection('health')} style={{ display: 'flex', alignItems: 'center', padding: '10px 16px', cursor: 'pointer', gap: 8 }}>
              <Zap size={14} style={{ color: 'var(--accent)' }} />
              <span style={{ fontWeight: 500, fontSize: 13 }}>{t('monitoring.health', '健康度评分')}</span>
              {health && <span style={{ marginLeft: 'auto', fontSize: 16, fontWeight: 700, color: health.overall >= 80 ? '#22c55e' : health.overall >= 50 ? '#eab308' : '#ef4444' }}>{health.overall.toFixed(0)}</span>}
              {expandedSection === 'health' ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </div>
            {expandedSection === 'health' && health && (
              <div style={{ padding: '0 16px 12px', display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
                <ScoreRing score={health.api_latency} label={t('monitoring.apiLatency', 'API延迟')} />
                <ScoreRing score={health.error_rate} label={t('monitoring.errorRate', '错误率')} />
                <ScoreRing score={health.resource_usage} label={t('monitoring.resourceUsage', '资源使用')} />
              </div>
            )}
          </div>

          {/* System Resources */}
          <div style={{ borderBottom: '1px solid var(--hairline)' }}>
            <div onClick={() => toggleSection('system')} style={{ display: 'flex', alignItems: 'center', padding: '10px 16px', cursor: 'pointer', gap: 8 }}>
              <Cpu size={14} style={{ color: 'var(--accent)' }} />
              <span style={{ fontWeight: 500, fontSize: 13 }}>{t('monitoring.system', '系统资源')}</span>
              {expandedSection === 'system' ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </div>
            {expandedSection === 'system' && system?.current && (
              <div style={{ padding: '0 16px 12px', display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 3 }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><Cpu size={10} /> CPU</span>
                    <span>{system.current.cpu_percent.toFixed(1)}%</span>
                  </div>
                  <MiniBar value={system.current.cpu_percent} max={100} color={system.current.cpu_percent > 80 ? '#ef4444' : system.current.cpu_percent > 60 ? '#eab308' : '#22c55e'} />
                </div>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 3 }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><Server size={10} /> {t('monitoring.memory', '内存')}</span>
                    <span>{system.current.memory_percent.toFixed(1)}% ({formatBytes(system.current.memory_used_mb)} / {formatBytes(system.current.memory_total_mb)})</span>
                  </div>
                  <MiniBar value={system.current.memory_percent} max={100} color={system.current.memory_percent > 80 ? '#ef4444' : system.current.memory_percent > 60 ? '#eab308' : '#22c55e'} />
                </div>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 3 }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><HardDrive size={10} /> {t('monitoring.disk', '磁盘')}</span>
                    <span>{system.current.disk_percent.toFixed(1)}% ({system.current.disk_used_gb.toFixed(1)} / {system.current.disk_total_gb.toFixed(1)} GB)</span>
                  </div>
                  <MiniBar value={system.current.disk_percent} max={100} color={system.current.disk_percent > 90 ? '#ef4444' : '#eab308'} />
                </div>
                {health?.details?.uptime_seconds && (
                  <div style={{ fontSize: 11, color: 'var(--mute)', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Clock size={10} /> {t('monitoring.uptime', '运行时间')}: {formatUptime(health.details.uptime_seconds as number)}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* API Request Stats */}
          <div style={{ borderBottom: '1px solid var(--hairline)' }}>
            <div onClick={() => toggleSection('requests')} style={{ display: 'flex', alignItems: 'center', padding: '10px 16px', cursor: 'pointer', gap: 8 }}>
              <Activity size={14} style={{ color: 'var(--accent)' }} />
              <span style={{ fontWeight: 500, fontSize: 13 }}>{t('monitoring.requests', 'API请求')}</span>
              {requests && <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--mute)' }}>{requests.total_requests} / {requests.period_minutes}min</span>}
              {expandedSection === 'requests' ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </div>
            {expandedSection === 'requests' && requests && (
              <div style={{ padding: '0 16px 12px', fontSize: 12 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div style={{ background: 'var(--canvas)', borderRadius: 6, padding: '6px 10px' }}>
                    <div style={{ fontSize: 10, color: 'var(--mute)' }}>{t('monitoring.avgLatency', '平均延迟')}</div>
                    <div style={{ fontWeight: 600 }}>{requests.avg_latency_ms?.toFixed(1) ?? '-'} ms</div>
                  </div>
                  <div style={{ background: 'var(--canvas)', borderRadius: 6, padding: '6px 10px' }}>
                    <div style={{ fontSize: 10, color: 'var(--mute)' }}>P99</div>
                    <div style={{ fontWeight: 600 }}>{requests.p99_latency_ms?.toFixed(1) ?? '-'} ms</div>
                  </div>
                  <div style={{ background: 'var(--canvas)', borderRadius: 6, padding: '6px 10px' }}>
                    <div style={{ fontSize: 10, color: 'var(--mute)' }}>{t('monitoring.errorCount', '错误数')}</div>
                    <div style={{ fontWeight: 600, color: (requests.error_count ?? 0) > 0 ? '#ef4444' : 'var(--ink)' }}>{requests.error_count ?? 0}</div>
                  </div>
                  <div style={{ background: 'var(--canvas)', borderRadius: 6, padding: '6px 10px' }}>
                    <div style={{ fontSize: 10, color: 'var(--mute)' }}>{t('monitoring.errorRate', '错误率')}</div>
                    <div style={{ fontWeight: 600 }}>{((requests.error_rate ?? 0) * 100).toFixed(2)}%</div>
                  </div>
                </div>

                {data?.slowest_endpoints && data.slowest_endpoints.length > 0 && (
                  <div style={{ marginTop: 10 }}>
                    <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--mute)', marginBottom: 4 }}>{t('monitoring.slowestEndpoints', '最慢端点')}</div>
                    {data.slowest_endpoints.map((ep) => (
                      <div key={ep.path} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', fontSize: 11 }}>
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '60%' }}>{ep.path}</span>
                        <span style={{ color: ep.p99_ms > 2000 ? '#ef4444' : 'var(--ink)' }}>{ep.p99_ms.toFixed(0)}ms</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Web Vitals */}
          <div style={{ borderBottom: '1px solid var(--hairline)' }}>
            <div onClick={() => toggleSection('vitals')} style={{ display: 'flex', alignItems: 'center', padding: '10px 16px', cursor: 'pointer', gap: 8 }}>
              <TrendingUp size={14} style={{ color: 'var(--accent)' }} />
              <span style={{ fontWeight: 500, fontSize: 13 }}>{t('monitoring.webVitals', 'Web Vitals')}</span>
              {expandedSection === 'vitals' ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </div>
            {expandedSection === 'vitals' && webVitals && (
              <div style={{ padding: '0 16px 12px', fontSize: 12 }}>
                {webVitals.total_reports === 0 ? (
                  <div style={{ color: 'var(--mute)', textAlign: 'center', padding: 12, fontSize: 12 }}>
                    {t('monitoring.noVitals', '暂无 Web Vitals 数据')}
                  </div>
                ) : (
                  Object.entries(webVitals.metrics || {}).map(([name, stats]) => (
                    <div key={name} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid var(--hairline)' }}>
                      <span style={{ fontWeight: 500 }}>{name}</span>
                      <span style={{ color: 'var(--mute)' }}>P75: {stats.p75.toFixed(1)} | {t('monitoring.worst', '最差')}: {stats.worst.toFixed(1)}</span>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Top Errors */}
          {data?.top_errors && data.top_errors.length > 0 && (
            <div style={{ borderBottom: '1px solid var(--hairline)' }}>
              <div onClick={() => toggleSection('errors')} style={{ display: 'flex', alignItems: 'center', padding: '10px 16px', cursor: 'pointer', gap: 8 }}>
                <AlertTriangle size={14} style={{ color: '#ef4444' }} />
                <span style={{ fontWeight: 500, fontSize: 13 }}>{t('monitoring.topErrors', '高频错误')}</span>
                {expandedSection === 'errors' ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </div>
              {expandedSection === 'errors' && (
                <div style={{ padding: '0 16px 12px', fontSize: 12 }}>
                  {data.top_errors.map((err) => (
                    <div key={err.error} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', fontSize: 11 }}>
                      <span style={{ color: '#ef4444', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '80%' }}>{err.error}</span>
                      <span style={{ color: 'var(--mute)' }}>×{err.count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
};
