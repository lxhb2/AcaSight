import React, { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  CheckCircle2, Clock, Circle, AlertTriangle, ChevronRight,
  FolderOpen, FileCode, FileText, Timer, GitBranch, Tag, Calendar,
} from 'lucide-react';

/* ───────── 类型定义 ───────── */

export type TaskStatus = 'done' | 'in-progress' | 'pending' | 'blocked';

export interface DevLogTask {
  id: string;
  phase: string;
  title: string;
  status: TaskStatus;
  developer: 'A' | 'B' | 'A+B';
  description?: string;
  files?: { path: string; action: 'created' | 'modified' | 'deleted' }[];
  codeSnippet?: string;
  duration?: string;
  tags?: string[];
  dependsOn?: string[];
}

export interface DevLogPhase {
  name: string;
  color: string;       // tailwind 颜色或 CSS 变量
  accentColor: string;
  tasks: DevLogTask[];
}

export interface DevLogData {
  projectName: string;
  version: string;
  date: string;
  phases: DevLogPhase[];
}

/* ───────── 工具函数 ───────── */

const statusIcon: Record<TaskStatus, React.ReactNode> = {
  done: <CheckCircle2 size={14} style={{ color: '#22c55e' }} />,
  'in-progress': <Clock size={14} style={{ color: '#3b82f6' }} />,
  pending: <Circle size={14} style={{ color: '#64748b' }} />,
  blocked: <AlertTriangle size={14} style={{ color: '#ef4444' }} />,
};

const statusLabel: Record<TaskStatus, string> = {
  done: '✅ 完成',
  'in-progress': '🔄 进行中',
  pending: '🔲 待办',
  blocked: '⚠️ 阻塞',
};

const actionColor: Record<string, string> = {
  created: '#22c55e',
  modified: '#3b82f6',
  deleted: '#ef4444',
};

/* ───────── 进度环组件 ───────── */

function ProgressRing({ percent, size = 64, strokeWidth = 5 }: { percent: number; size?: number; strokeWidth?: number }) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percent / 100) * circumference;
  const color = percent >= 80 ? '#22c55e' : percent >= 50 ? '#eab308' : '#ef4444';

  return (
    <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
      <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--hairline)" strokeWidth={strokeWidth} />
      <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={color} strokeWidth={strokeWidth}
        strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round"
        style={{ transition: 'stroke-dashoffset 0.6s ease' }} />
    </svg>
  );
}

/* ───────── 进度条组件 ───────── */

function ProgressBar({ percent, color = 'var(--accent)' }: { percent: number; color?: string }) {
  return (
    <div style={{ height: 4, borderRadius: 2, background: 'var(--hairline)', overflow: 'hidden', flex: 1 }}>
      <div style={{ height: '100%', width: `${percent}%`, background: color, borderRadius: 2, transition: 'width 0.4s ease' }} />
    </div>
  );
}

/* ───────── 主组件 ───────── */

interface DevLogPanelProps {
  data?: DevLogData;
}

export const DevLogPanel: React.FC<DevLogPanelProps> = ({ data: propData }) => {
  const { t } = useTranslation();
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [defaultData, setDefaultData] = useState<DevLogData | null>(null);

  // 延迟加载默认数据
  React.useEffect(() => {
    if (!propData) {
      import('@/data/phase11DevLog').then(mod => setDefaultData(mod.phase11DevLog)).catch(() => {});
    }
  }, [propData]);

  const data = propData ?? defaultData;

  if (!data) return <div style={{ padding: 32, textAlign: 'center', color: 'var(--mute)' }}>Loading dev log...</div>;

  /* 计算统计 */
  const allTasks = useMemo(() => data.phases.flatMap(p => p.tasks), [data.phases]);
  const stats = useMemo(() => {
    const done = allTasks.filter(t => t.status === 'done').length;
    const inProgress = allTasks.filter(t => t.status === 'in-progress').length;
    const pending = allTasks.filter(t => t.status === 'pending').length;
    const blocked = allTasks.filter(t => t.status === 'blocked').length;
    const percent = allTasks.length > 0 ? Math.round((done / allTasks.length) * 100) : 0;
    return { done, inProgress, pending, blocked, total: allTasks.length, percent };
  }, [allTasks]);

  const selectedTask = useMemo(() => allTasks.find(t => t.id === selectedTaskId), [allTasks, selectedTaskId]);

  /* 按阶段分组进度 */
  const phaseStats = useMemo(() => data.phases.map(p => {
    const done = p.tasks.filter(t => t.status === 'done').length;
    const percent = p.tasks.length > 0 ? Math.round((done / p.tasks.length) * 100) : 0;
    return { name: p.name, percent, done, total: p.tasks.length, color: p.color };
  }), [data.phases]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', color: 'var(--ink)', background: 'var(--bg-primary)' }}>
      {/* ═══ 顶部项目信息卡 ═══ */}
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid var(--hairline)',
        background: 'linear-gradient(135deg, rgba(99,102,241,0.08) 0%, rgba(59,130,246,0.04) 100%)',
      }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
          {/* 进度环 */}
          <div style={{ position: 'relative', flexShrink: 0 }}>
            <ProgressRing percent={stats.percent} size={72} strokeWidth={5} />
            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
              <span style={{ fontSize: 18, fontWeight: 700, lineHeight: 1 }}>{stats.percent}%</span>
              <span style={{ fontSize: 9, color: 'var(--mute)' }}>progress</span>
            </div>
          </div>

          {/* 项目信息 */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <span style={{ fontSize: 18, fontWeight: 700, letterSpacing: '-0.02em' }}>{data.projectName}</span>
              <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, background: 'var(--accent)', color: '#fff', fontWeight: 600 }}>
                {data.version}
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 11, color: 'var(--mute)', marginBottom: 8 }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}><Calendar size={10} /> {data.date}</span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}><GitBranch size={10} /> {stats.total} tasks</span>
            </div>

            {/* 状态统计条 */}
            <div style={{ display: 'flex', gap: 10, fontSize: 11 }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 3, color: '#22c55e' }}>
                <CheckCircle2 size={11} /> {stats.done}
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 3, color: '#3b82f6' }}>
                <Clock size={11} /> {stats.inProgress}
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 3, color: '#64748b' }}>
                <Circle size={11} /> {stats.pending}
              </span>
              {stats.blocked > 0 && (
                <span style={{ display: 'flex', alignItems: 'center', gap: 3, color: '#ef4444' }}>
                  <AlertTriangle size={11} /> {stats.blocked}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* 阶段进度条 */}
        <div style={{ display: 'flex', gap: 6, marginTop: 12, flexWrap: 'wrap' }}>
          {phaseStats.map(ps => (
            <div key={ps.name} style={{ flex: 1, minWidth: 80 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--mute)', marginBottom: 2 }}>
                <span>{ps.name}</span>
                <span>{ps.done}/{ps.total}</span>
              </div>
              <ProgressBar percent={ps.percent} color={ps.color} />
            </div>
          ))}
        </div>
      </div>

      {/* ═══ 主体：任务列表 + 详情 ═══ */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* 左侧任务列表 */}
        <div style={{ width: 260, borderRight: '1px solid var(--hairline)', overflow: 'auto', flexShrink: 0 }}>
          {data.phases.map(phase => (
            <div key={phase.name}>
              {/* 阶段标题 */}
              <div style={{
                padding: '8px 16px',
                fontSize: 11,
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                color: phase.accentColor,
                background: `linear-gradient(90deg, ${phase.color}15 0%, transparent 100%)`,
                borderBottom: '1px solid var(--hairline)',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}>
                <span style={{ width: 8, height: 8, borderRadius: 2, background: phase.color }} />
                {phase.name}
              </div>

              {/* 任务列表 */}
              {phase.tasks.map(task => (
                <div
                  key={task.id}
                  onClick={() => setSelectedTaskId(task.id === selectedTaskId ? null : task.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    padding: '8px 16px',
                    cursor: 'pointer',
                    borderBottom: '1px solid var(--hairline)',
                    background: selectedTaskId === task.id ? 'rgba(99,102,241,0.08)' : 'transparent',
                    transition: 'background 0.15s',
                  }}
                  onMouseEnter={e => { if (selectedTaskId !== task.id) (e.currentTarget as HTMLDivElement).style.background = 'var(--canvas)'; }}
                  onMouseLeave={e => { if (selectedTaskId !== task.id) (e.currentTarget as HTMLDivElement).style.background = 'transparent'; }}
                >
                  {statusIcon[task.status]}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      <span style={{ color: 'var(--mute)', fontSize: 10, marginRight: 4 }}>{task.id}</span>
                      {task.title}
                    </div>
                  </div>
                  <span style={{
                    fontSize: 9, padding: '1px 5px', borderRadius: 3,
                    background: task.developer === 'A' ? 'rgba(59,130,246,0.15)' : task.developer === 'B' ? 'rgba(168,85,247,0.15)' : 'rgba(34,197,94,0.15)',
                    color: task.developer === 'A' ? '#3b82f6' : task.developer === 'B' ? '#a855f7' : '#22c55e',
                    fontWeight: 600,
                  }}>
                    {task.developer}
                  </span>
                  {selectedTaskId === task.id && <ChevronRight size={12} style={{ color: 'var(--accent)' }} />}
                </div>
              ))}
            </div>
          ))}
        </div>

        {/* 右侧详情面板 */}
        <div style={{ flex: 1, overflow: 'auto' }}>
          {selectedTask ? (
            <div style={{ padding: 20 }}>
              {/* 标题行 */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <span style={{ fontSize: 11, color: 'var(--mute)', fontFamily: 'monospace' }}>{selectedTask.id}</span>
                <span style={{ fontSize: 16, fontWeight: 700, flex: 1 }}>{selectedTask.title}</span>
                <span style={{
                  fontSize: 11, padding: '3px 10px', borderRadius: 6,
                  background: selectedTask.status === 'done' ? 'rgba(34,197,94,0.15)' :
                    selectedTask.status === 'in-progress' ? 'rgba(59,130,246,0.15)' :
                    selectedTask.status === 'blocked' ? 'rgba(239,68,68,0.15)' : 'rgba(100,116,139,0.15)',
                  color: selectedTask.status === 'done' ? '#22c55e' :
                    selectedTask.status === 'in-progress' ? '#3b82f6' :
                    selectedTask.status === 'blocked' ? '#ef4444' : '#64748b',
                  fontWeight: 600,
                }}>
                  {statusLabel[selectedTask.status]}
                </span>
              </div>

              {/* 元信息 */}
              <div style={{ display: 'flex', gap: 16, fontSize: 12, color: 'var(--mute)', marginBottom: 16, flexWrap: 'wrap' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span style={{
                    width: 18, height: 18, borderRadius: 4, display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 10, fontWeight: 700,
                    background: selectedTask.developer === 'A' ? 'rgba(59,130,246,0.2)' : selectedTask.developer === 'B' ? 'rgba(168,85,247,0.2)' : 'rgba(34,197,94,0.2)',
                    color: selectedTask.developer === 'A' ? '#3b82f6' : selectedTask.developer === 'B' ? '#a855f7' : '#22c55e',
                  }}>
                    {selectedTask.developer}
                  </span>
                  Developer {selectedTask.developer}
                </span>
                {selectedTask.duration && (
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><Timer size={12} /> {selectedTask.duration}</span>
                )}
                {selectedTask.dependsOn && selectedTask.dependsOn.length > 0 && (
                  <span>Depends: {selectedTask.dependsOn.join(', ')}</span>
                )}
              </div>

              {/* 描述 */}
              {selectedTask.description && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--mute)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Description
                  </div>
                  <div style={{ fontSize: 13, lineHeight: 1.7, color: 'var(--ink)' }}>
                    {selectedTask.description}
                  </div>
                </div>
              )}

              {/* 标签 */}
              {selectedTask.tags && selectedTask.tags.length > 0 && (
                <div style={{ display: 'flex', gap: 4, marginBottom: 16, flexWrap: 'wrap' }}>
                  {selectedTask.tags.map(tag => (
                    <span key={tag} style={{
                      fontSize: 10, padding: '2px 8px', borderRadius: 4,
                      background: 'var(--canvas)', border: '1px solid var(--hairline)',
                      display: 'flex', alignItems: 'center', gap: 3, color: 'var(--mute)',
                    }}>
                      <Tag size={8} />{tag}
                    </span>
                  ))}
                </div>
              )}

              {/* 文件变更列表 */}
              {selectedTask.files && selectedTask.files.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--mute)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    File Changes ({selectedTask.files.length})
                  </div>
                  <div style={{ borderRadius: 8, border: '1px solid var(--hairline)', overflow: 'hidden' }}>
                    {selectedTask.files.map((file, i) => (
                      <div key={i} style={{
                        display: 'flex', alignItems: 'center', gap: 8,
                        padding: '6px 12px', fontSize: 12,
                        borderBottom: i < selectedTask.files!.length - 1 ? '1px solid var(--hairline)' : 'none',
                        background: 'var(--canvas)',
                      }}>
                        {file.action === 'created' ? <FileCode size={12} style={{ color: '#22c55e' }} /> :
                         file.action === 'deleted' ? <FileText size={12} style={{ color: '#ef4444' }} /> :
                         <FileText size={12} style={{ color: '#3b82f6' }} />}
                        <span style={{ flex: 1, fontFamily: 'monospace', fontSize: 11, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {file.path}
                        </span>
                        <span style={{
                          fontSize: 9, padding: '1px 6px', borderRadius: 3,
                          background: `${actionColor[file.action]}20`, color: actionColor[file.action],
                          fontWeight: 600, textTransform: 'uppercase',
                        }}>
                          {file.action}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 代码片段 */}
              {selectedTask.codeSnippet && (
                <div>
                  <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--mute)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Code Snippet
                  </div>
                  <pre style={{
                    padding: 12, borderRadius: 8, fontSize: 11, lineHeight: 1.6,
                    background: 'var(--canvas)', border: '1px solid var(--hairline)',
                    fontFamily: 'monospace', whiteSpace: 'pre-wrap', wordBreak: 'break-all',
                    maxHeight: 300, overflow: 'auto', color: 'var(--ink)',
                  }}>
                    {selectedTask.codeSnippet}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            /* 空状态 */
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 8 }}>
              <FolderOpen size={32} style={{ color: 'var(--mute)', opacity: 0.5 }} />
              <span style={{ fontSize: 13, color: 'var(--mute)' }}>{t('devLog.selectTask', '选择左侧任务查看详情')}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
