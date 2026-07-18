/**
 * PlotStudio — 统一科研绘图中心
 * 整合 XRD / Raman / XPS / FTIR / UV-Vis / TGA-DSC / BET / RSM / 光谱处理 / 统计分析 / 通用绘图
 * 参考 Origin/DMSAS/JMP 专业绘图软件交互模式
 */
import React, { useState, useCallback, Suspense, lazy } from 'react';
import { useTranslation } from 'react-i18next';
import {
  FlaskConical, Box, Waves, BarChart3, TrendingUp,
  ChevronRight, Download, Palette, Sparkles,
  Atom, Sun, Thermometer, Droplets, Beaker,
  LayoutGrid, BookOpen,
} from 'lucide-react';

/* ── Lazy sub-modules ── */
const XRDStackedChart = lazy(() => import('@/components/Charts/Materials/XRD/XRDStackedChart').then(m => ({ default: m.XRDStackedChart })));
const ResponseSurface3D = lazy(() => import('@/components/Charts/DOE/ResponseSurface3D').then(m => ({ default: m.ResponseSurface3D })));
const SpectrumProcessor = lazy(() => import('@/components/Charts/Common/SpectrumProcessor').then(m => ({ default: m.SpectrumProcessor })));
const StatisticsPanel = lazy(() => import('@/components/Charts/Statistics/StatisticsPanel').then(m => ({ default: m.StatisticsPanel })));
const ChartPanel = lazy(() => import('@/components/Charts/ChartPanel').then(m => ({ default: m.ChartPanel })));

/* ── Types ── */
interface NavCategory {
  id: string;
  labelKey: string;
  icon: typeof FlaskConical;
  color: string;
  children: NavItem[];
}

interface NavItem {
  id: string;
  labelKey: string;
  icon: typeof FlaskConical;
  badge?: string;
}

/* ── Navigation config ── */
const NAV_CATEGORIES: NavCategory[] = [
  {
    id: 'materials',
    labelKey: 'plotStudio.materials',
    icon: FlaskConical,
    color: '#059669',
    children: [
      { id: 'xrd', labelKey: 'plotStudio.xrd', icon: Atom },
      { id: 'raman', labelKey: 'plotStudio.raman', icon: Waves },
      { id: 'xps', labelKey: 'plotStudio.xps', icon: Beaker },
      { id: 'ftir', labelKey: 'plotStudio.ftir', icon: Droplets },
      { id: 'uvvis', labelKey: 'plotStudio.uvvis', icon: Sun },
      { id: 'tga-dsc', labelKey: 'plotStudio.tgaDsc', icon: Thermometer },
      { id: 'bet', labelKey: 'plotStudio.bet', icon: Droplets },
    ],
  },
  {
    id: 'doe',
    labelKey: 'plotStudio.doe',
    icon: Box,
    color: '#7c3aed',
    children: [
      { id: 'rsm-3d', labelKey: 'plotStudio.rsm3d', icon: Box },
      { id: 'spectrum', labelKey: 'plotStudio.spectrumProcess', icon: Waves },
    ],
  },
  {
    id: 'statistics',
    labelKey: 'plotStudio.statistics',
    icon: BarChart3,
    color: '#dc2626',
    children: [
      { id: 'stats', labelKey: 'plotStudio.statsAnalysis', icon: BarChart3 },
    ],
  },
  {
    id: 'general',
    labelKey: 'plotStudio.general',
    icon: TrendingUp,
    color: '#9DB4AB',
    children: [
      { id: 'origin', labelKey: 'plotStudio.originPlot', icon: TrendingUp },
    ],
  },
];

/* ── Skeleton ── */
function ModuleSkeleton() {
  return (
    <div style={{ padding: 24 }}>
      <div style={{ width: '40%', height: 20, background: 'var(--bg-secondary)', borderRadius: 6, marginBottom: 16 }} />
      <div style={{ width: '100%', height: 300, background: 'var(--bg-secondary)', borderRadius: 8 }} />
    </div>
  );
}

/* ── Component ── */
interface PlotStudioProps {
  onClose: () => void;
}

export const PlotStudio: React.FC<PlotStudioProps> = ({ onClose: _onClose }) => {
  const { t } = useTranslation();
  const [activeModule, setActiveModule] = useState('xrd');
  const [expandedCategory, setExpandedCategory] = useState('materials');
  const [showThemeSelector, setShowThemeSelector] = useState(false);

  /* ── Find active module info ── */
  const findActiveItem = useCallback(() => {
    for (const cat of NAV_CATEGORIES) {
      for (const child of cat.children) {
        if (child.id === activeModule) return { category: cat, item: child };
      }
    }
    return null;
  }, [activeModule]);

  const activeInfo = findActiveItem();

  /* ── Render module content ── */
  const renderModule = () => {
    switch (activeModule) {
      case 'xrd':
        return <XRDStackedChart />;
      case 'rsm-3d':
        return <ResponseSurface3D />;
      case 'spectrum':
      case 'raman':
      case 'xps':
      case 'ftir':
      case 'uvvis':
      case 'tga-dsc':
      case 'bet':
        return <SpectrumProcessor defaultSpectrumType={activeModule} />;
      case 'stats':
        return <StatisticsPanel />;
      case 'origin':
        return <ChartPanel />;
      default:
        return <ModuleSkeleton />;
    }
  };

  /* ── Handle nav click ── */
  const handleNavClick = (categoryId: string, itemId: string) => {
    setExpandedCategory(categoryId);
    setActiveModule(itemId);
  };

  return (
    <div style={{ display: 'flex', height: '100%', background: 'var(--canvas)' }}>
      {/* ── Left sidebar navigation ── */}
      <div style={{
        width: 220, flexShrink: 0,
        borderRight: '1px solid var(--hairline)',
        background: 'var(--bg-2, var(--bg-secondary))',
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden',
      }}>
        {/* Sidebar header */}
        <div style={{
          padding: '12px 14px',
          borderBottom: '1px solid var(--hairline)',
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <LayoutGrid size={18} style={{ color: 'var(--accent)' }} />
          <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--body)' }}>
            {t('plotStudio.title')}
          </span>
        </div>

        {/* Nav categories */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '6px 0' }}>
          {NAV_CATEGORIES.map(cat => {
            const isExpanded = expandedCategory === cat.id;
            const hasActiveChild = cat.children.some(c => c.id === activeModule);
            return (
              <div key={cat.id}>
                {/* Category header */}
                <button
                  onClick={() => setExpandedCategory(isExpanded ? '' : cat.id)}
                  style={{
                    display: 'flex', alignItems: 'center', width: '100%',
                    padding: '8px 14px', gap: 8,
                    background: hasActiveChild ? 'var(--bg-tertiary, rgba(0,0,0,0.04))' : 'transparent',
                    border: 'none', cursor: 'pointer', color: 'var(--body)',
                    fontSize: 13, fontWeight: 600, textAlign: 'left',
                  }}
                >
                  <cat.icon size={16} style={{ color: cat.color, flexShrink: 0 }} />
                  <span style={{ flex: 1 }}>{t(cat.labelKey)}</span>
                  <ChevronRight
                    size={14}
                    style={{
                      color: 'var(--mute)',
                      transform: isExpanded ? 'rotate(90deg)' : 'rotate(0)',
                      transition: 'transform 0.15s',
                    }}
                  />
                </button>

                {/* Children */}
                {isExpanded && cat.children.map(item => {
                  const isActive = activeModule === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => handleNavClick(cat.id, item.id)}
                      style={{
                        display: 'flex', alignItems: 'center', width: '100%',
                        padding: '6px 14px 6px 38px', gap: 8,
                        background: isActive
                          ? `linear-gradient(90deg, ${cat.color}18, transparent)`
                          : 'transparent',
                        border: 'none', cursor: 'pointer',
                        borderLeft: isActive ? `3px solid ${cat.color}` : '3px solid transparent',
                        color: isActive ? cat.color : 'var(--body)',
                        fontSize: 12.5, fontWeight: isActive ? 600 : 400,
                        textAlign: 'left',
                      }}
                    >
                      <item.icon size={14} style={{ flexShrink: 0 }} />
                      <span style={{ flex: 1 }}>{t(item.labelKey)}</span>
                      {item.badge && (
                        <span style={{
                          fontSize: 10, padding: '1px 6px', borderRadius: 8,
                          background: cat.color, color: '#fff', fontWeight: 600,
                        }}>
                          {item.badge}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            );
          })}
        </div>

        {/* Sidebar footer - quick links */}
        <div style={{
          padding: '8px 14px',
          borderTop: '1px solid var(--hairline)',
          display: 'flex', gap: 4,
        }}>
          <button
            onClick={() => setShowThemeSelector(!showThemeSelector)}
            style={{
              flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
              padding: '6px 0', borderRadius: 6,
              background: 'var(--bg-tertiary, rgba(0,0,0,0.04))',
              border: 'none', cursor: 'pointer', color: 'var(--body)',
              fontSize: 11,
            }}
            title={t('plotStudio.themeSelector')}
          >
            <Palette size={13} />
            <span>{t('plotStudio.theme')}</span>
          </button>
        </div>
      </div>

      {/* ── Right content area ── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Top toolbar */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '8px 16px',
          borderBottom: '1px solid var(--hairline)',
          background: 'var(--bg-2, var(--bg-secondary))',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {activeInfo && (
              <>
                <activeInfo.item.icon size={16} style={{ color: activeInfo.category.color }} />
                <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--body)' }}>
                  {t(activeInfo.item.labelKey)}
                </span>
                <span style={{
                  fontSize: 11, padding: '2px 8px', borderRadius: 8,
                  background: `${activeInfo.category.color}20`, color: activeInfo.category.color,
                  fontWeight: 500,
                }}>
                  {t(activeInfo.category.labelKey)}
                </span>
              </>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <button
              style={{
                display: 'flex', alignItems: 'center', gap: 4,
                padding: '4px 10px', borderRadius: 6, fontSize: 12,
                background: 'var(--bg-tertiary, rgba(0,0,0,0.04))',
                border: '1px solid var(--hairline)', cursor: 'pointer',
                color: 'var(--body)',
              }}
              title={t('plotStudio.aiAssist')}
            >
              <Sparkles size={13} />
              <span>{t('plotStudio.aiAssist')}</span>
            </button>
            <button
              style={{
                display: 'flex', alignItems: 'center', gap: 4,
                padding: '4px 10px', borderRadius: 6, fontSize: 12,
                background: 'var(--bg-tertiary, rgba(0,0,0,0.04))',
                border: '1px solid var(--hairline)', cursor: 'pointer',
                color: 'var(--body)',
              }}
              title={t('plotStudio.export')}
            >
              <Download size={13} />
              <span>{t('plotStudio.export')}</span>
            </button>
            <button
              style={{
                display: 'flex', alignItems: 'center', gap: 4,
                padding: '4px 10px', borderRadius: 6, fontSize: 12,
                background: 'var(--bg-tertiary, rgba(0,0,0,0.04))',
                border: '1px solid var(--hairline)', cursor: 'pointer',
                color: 'var(--body)',
              }}
              title={t('plotStudio.docs')}
            >
              <BookOpen size={13} />
            </button>
          </div>
        </div>

        {/* Module content */}
        <div style={{ flex: 1, overflow: 'auto' }}>
          <Suspense fallback={<ModuleSkeleton />}>
            {renderModule()}
          </Suspense>
        </div>
      </div>
    </div>
  );
};
