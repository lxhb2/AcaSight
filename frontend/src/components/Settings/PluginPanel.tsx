import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Puzzle, Loader2, CheckCircle2, XCircle, Power, PowerOff,
  Trash2, Search, Zap, ChevronDown, ChevronUp, AlertTriangle,
  RefreshCw,
} from 'lucide-react';
import { pluginsApi, type PluginInfo, type HookResult } from '@/services/api';

const STATE_COLORS: Record<string, { bg: string; color: string }> = {
  loaded: { bg: 'rgba(59,130,246,0.12)', color: '#3b82f6' },
  enabled: { bg: 'rgba(34,197,94,0.12)', color: '#22c55e' },
  disabled: { bg: 'rgba(107,114,128,0.12)', color: '#6b7280' },
  error: { bg: 'var(--danger-soft)', color: 'var(--danger)' },
};

export const PluginPanel: React.FC = () => {
  const { t } = useTranslation();

  const [plugins, setPlugins] = useState<PluginInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [discovered, setDiscovered] = useState<{ plugins_dir: string; discovered: string[]; count: number } | null>(null);
  const [discovering, setDiscovering] = useState(false);
  const [loadingPlugin, setLoadingPlugin] = useState<string | null>(null);
  const [actioningPlugin, setActioningPlugin] = useState<string | null>(null);

  const [hookName, setHookName] = useState('');
  const [hookKwargs, setHookKwargs] = useState('{}');
  const [hookTriggering, setHookTriggering] = useState(false);
  const [hookResults, setHookResults] = useState<{ hook_name: string; handlers_called: number; results: HookResult[] } | null>(null);
  const [hookError, setHookError] = useState<string | null>(null);

  const [expandedPlugin, setExpandedPlugin] = useState<string | null>(null);
  const [expandedDiscover, setExpandedDiscover] = useState(false);
  const [expandedHook, setExpandedHook] = useState(false);

  const fetchPlugins = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await pluginsApi.list();
      if (res.success && res.data) {
        setPlugins(res.data);
      } else {
        setError(t('plugin.fetchFailed'));
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchPlugins();
  }, [fetchPlugins]);

  const handleDiscover = useCallback(async () => {
    setDiscovering(true);
    try {
      const res = await pluginsApi.discover();
      if (res.success && res.data) {
        setDiscovered(res.data);
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setDiscovering(false);
    }
  }, []);

  const handleLoad = useCallback(async (pluginPath: string) => {
    setLoadingPlugin(pluginPath);
    try {
      await pluginsApi.load(pluginPath);
      await fetchPlugins();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setLoadingPlugin(null);
    }
  }, [fetchPlugins]);

  const handleEnable = useCallback(async (name: string) => {
    setActioningPlugin(name);
    try {
      await pluginsApi.enable(name);
      await fetchPlugins();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setActioningPlugin(null);
    }
  }, [fetchPlugins]);

  const handleDisable = useCallback(async (name: string) => {
    setActioningPlugin(name);
    try {
      await pluginsApi.disable(name);
      await fetchPlugins();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setActioningPlugin(null);
    }
  }, [fetchPlugins]);

  const handleUnload = useCallback(async (name: string) => {
    setActioningPlugin(name);
    try {
      await pluginsApi.unload(name);
      await fetchPlugins();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setActioningPlugin(null);
    }
  }, [fetchPlugins]);

  const handleTriggerHook = useCallback(async () => {
    if (!hookName.trim()) return;
    setHookTriggering(true);
    setHookError(null);
    setHookResults(null);
    try {
      let kwargs = {};
      if (hookKwargs.trim()) {
        kwargs = JSON.parse(hookKwargs);
      }
      const res = await pluginsApi.triggerHook(hookName, kwargs);
      if (res.success && res.data) {
        setHookResults(res.data);
      } else {
        setHookError(t('plugin.hookFailed'));
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setHookError(msg);
    } finally {
      setHookTriggering(false);
    }
  }, [hookName, hookKwargs, t]);

  const togglePlugin = useCallback((name: string) => {
    setExpandedPlugin(prev => prev === name ? null : name);
  }, []);

  const loadedNames = new Set(plugins.map(p => p.name));
  const unloadedDiscovered = discovered ? discovered.discovered.filter(d => !loadedNames.has(d)) : [];

  return (
    <div style={{ height: '100%', overflow: 'auto', padding: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
        <Puzzle size={18} style={{ color: 'var(--accent)' }} />
        <span style={{ fontSize: 16, fontWeight: 600, color: 'var(--ink)' }}>{t('plugin.title')}</span>
        <button
          onClick={fetchPlugins}
          disabled={loading}
          style={{
            marginLeft: 'auto', width: 28, height: 28, borderRadius: 'var(--radius-sm)',
            background: 'var(--canvas-soft)', border: '1px solid var(--hairline)',
            color: 'var(--body)', cursor: loading ? 'wait' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          <RefreshCw size={13} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
        </button>
      </div>

      {error && (
        <div style={{
          padding: '8px 12px', marginBottom: 16, borderRadius: 'var(--radius-sm)',
          background: 'var(--danger-soft)', border: '1px solid var(--danger)',
          display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--danger)',
        }}>
          <AlertTriangle size={13} />
          <span style={{ flex: 1 }}>{error}</span>
          <button onClick={() => setError(null)} style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer', padding: 0 }}>
            <XCircle size={14} />
          </button>
        </div>
      )}

      <div style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Puzzle size={14} /> {t('plugin.installed')}
          <span style={{ fontSize: 10, color: 'var(--mute)', fontWeight: 400, marginLeft: 4 }}>
            ({plugins.length})
          </span>
        </h3>

        {loading && plugins.length === 0 ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 32, color: 'var(--mute)', gap: 8, fontSize: 12 }}>
            <Loader2 size={16} className="animate-spin" /> {t('plugin.loading')}
          </div>
        ) : plugins.length === 0 ? (
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--mute)', fontSize: 12, borderRadius: 'var(--radius-sm)', background: 'var(--canvas-soft)', border: '1px solid var(--hairline)' }}>
            {t('plugin.noPlugins')}
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {plugins.map(plugin => {
              const stateStyle = STATE_COLORS[plugin.state] || STATE_COLORS.disabled;
              const isExpanded = expandedPlugin === plugin.name;
              const isActioning = actioningPlugin === plugin.name;

              return (
                <div key={plugin.name} style={{
                  borderRadius: 'var(--radius-sm)', border: '1px solid var(--hairline)',
                  background: 'var(--canvas)', overflow: 'hidden',
                }}>
                  <button
                    onClick={() => togglePlugin(plugin.name)}
                    style={{
                      width: '100%', display: 'flex', alignItems: 'center', gap: 10,
                      padding: '10px 12px', background: 'transparent', border: 'none',
                      cursor: 'pointer', textAlign: 'left' as const,
                    }}
                  >
                    <Puzzle size={14} style={{ color: 'var(--accent)', flexShrink: 0 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--ink)' }}>{plugin.name}</span>
                        <span style={{ fontSize: 10, color: 'var(--mute)' }}>v{plugin.version}</span>
                      </div>
                    </div>
                    <span style={{
                      fontSize: 10, padding: '2px 8px', borderRadius: 'var(--radius-sm)',
                      background: stateStyle.bg, color: stateStyle.color, fontWeight: 500,
                      flexShrink: 0,
                    }}>
                      {plugin.state}
                    </span>
                    {isExpanded ? <ChevronUp size={14} style={{ color: 'var(--mute)', flexShrink: 0 }} /> : <ChevronDown size={14} style={{ color: 'var(--mute)', flexShrink: 0 }} />}
                  </button>

                  {isExpanded && (
                    <div style={{ padding: '0 12px 12px', borderTop: '1px solid var(--hairline)' }}>
                      <div style={{ paddingTop: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>
                        {plugin.hooks.length > 0 && (
                          <div>
                            <span style={{ fontSize: 11, color: 'var(--mute)', fontWeight: 500 }}>{t('plugin.hooks')}</span>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
                              {plugin.hooks.map(hook => (
                                <span key={hook} style={{
                                  fontSize: 10, padding: '2px 6px', borderRadius: 'var(--radius-sm)',
                                  background: 'var(--accent-bg-soft)', color: 'var(--accent)',
                                }}>
                                  {hook}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {plugin.loaded_at !== null && (
                          <div style={{ fontSize: 11, color: 'var(--mute)' }}>
                            {t('plugin.loadedAt')}: {new Date(plugin.loaded_at * 1000).toLocaleString()}
                          </div>
                        )}

                        {plugin.error && (
                          <div style={{
                            fontSize: 11, color: 'var(--danger)', padding: '6px 10px',
                            borderRadius: 'var(--radius-sm)', background: 'var(--danger-soft)',
                            display: 'flex', alignItems: 'center', gap: 6,
                          }}>
                            <AlertTriangle size={12} />
                            {plugin.error}
                          </div>
                        )}

                        <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                          {plugin.state !== 'enabled' && (
                            <button
                              onClick={() => handleEnable(plugin.name)}
                              disabled={isActioning}
                              style={{
                                padding: '4px 10px', borderRadius: 'var(--radius-sm)',
                                background: 'var(--accent)', color: 'var(--on-primary)',
                                border: 'none', cursor: isActioning ? 'wait' : 'pointer',
                                fontSize: 11, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 4,
                                opacity: isActioning ? 0.6 : 1,
                              }}
                            >
                              {isActioning ? <Loader2 size={11} className="animate-spin" /> : <Power size={11} />}
                              {t('plugin.enable')}
                            </button>
                          )}
                          {plugin.state !== 'disabled' && plugin.state !== 'error' && (
                            <button
                              onClick={() => handleDisable(plugin.name)}
                              disabled={isActioning}
                              style={{
                                padding: '4px 10px', borderRadius: 'var(--radius-sm)',
                                background: 'var(--canvas-soft)', color: 'var(--body)',
                                border: '1px solid var(--hairline)', cursor: isActioning ? 'wait' : 'pointer',
                                fontSize: 11, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 4,
                                opacity: isActioning ? 0.6 : 1,
                              }}
                            >
                              {isActioning ? <Loader2 size={11} className="animate-spin" /> : <PowerOff size={11} />}
                              {t('plugin.disable')}
                            </button>
                          )}
                          <button
                            onClick={() => handleUnload(plugin.name)}
                            disabled={isActioning}
                            style={{
                              padding: '4px 10px', borderRadius: 'var(--radius-sm)',
                              background: 'var(--danger-soft)', color: 'var(--danger)',
                              border: '1px solid transparent', cursor: isActioning ? 'wait' : 'pointer',
                              fontSize: 11, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 4,
                              opacity: isActioning ? 0.6 : 1,
                            }}
                          >
                            {isActioning ? <Loader2 size={11} className="animate-spin" /> : <Trash2 size={11} />}
                            {t('plugin.unload')}
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div style={{ marginBottom: 24 }}>
        <button
          onClick={() => { setExpandedDiscover(prev => !prev); if (!discovered) handleDiscover(); }}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', gap: 8,
            padding: '10px 12px', borderRadius: 'var(--radius-sm)',
            background: 'var(--canvas)', border: '1px solid var(--hairline)',
            cursor: 'pointer', textAlign: 'left' as const,
          }}
        >
          <Search size={14} style={{ color: 'var(--accent)' }} />
          <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--ink)', flex: 1 }}>{t('plugin.discover')}</span>
          {discovering ? <Loader2 size={14} className="animate-spin" style={{ color: 'var(--mute)' }} /> : expandedDiscover ? <ChevronUp size={14} style={{ color: 'var(--mute)' }} /> : <ChevronDown size={14} style={{ color: 'var(--mute)' }} />}
        </button>

        {expandedDiscover && (
          <div style={{
            marginTop: 6, padding: 12, borderRadius: 'var(--radius-sm)',
            background: 'var(--canvas)', border: '1px solid var(--hairline)',
          }}>
            {discovered ? (
              <>
                <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 8 }}>
                  {t('plugin.pluginsDir')}: <code style={{ fontSize: 10, background: 'var(--accent-bg-soft)', padding: '1px 4px', borderRadius: 'var(--radius-sm)' }}>{discovered.plugins_dir}</code>
                </div>
                {unloadedDiscovered.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    {unloadedDiscovered.map(dp => (
                      <div key={dp} style={{
                        display: 'flex', alignItems: 'center', gap: 8,
                        padding: '6px 10px', borderRadius: 'var(--radius-sm)',
                        background: 'var(--canvas-soft)', border: '1px solid var(--hairline)',
                      }}>
                        <Puzzle size={12} style={{ color: 'var(--mute)', flexShrink: 0 }} />
                        <span style={{ fontSize: 12, color: 'var(--ink)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' as const }}>{dp}</span>
                        <button
                          onClick={() => handleLoad(dp)}
                          disabled={loadingPlugin === dp}
                          style={{
                            padding: '3px 8px', borderRadius: 'var(--radius-sm)',
                            background: 'var(--accent)', color: 'var(--on-primary)',
                            border: 'none', cursor: loadingPlugin === dp ? 'wait' : 'pointer',
                            fontSize: 10, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 3,
                            opacity: loadingPlugin === dp ? 0.6 : 1,
                          }}
                        >
                          {loadingPlugin === dp ? <Loader2 size={10} className="animate-spin" /> : <CheckCircle2 size={10} />}
                          {t('plugin.load')}
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: 11, color: 'var(--mute)', textAlign: 'center', padding: 8 }}>
                    {t('plugin.noNewPlugins')}
                  </div>
                )}
              </>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16, color: 'var(--mute)', gap: 8, fontSize: 12 }}>
                <Loader2 size={14} className="animate-spin" /> {t('plugin.discovering')}
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{ marginBottom: 24 }}>
        <button
          onClick={() => setExpandedHook(prev => !prev)}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', gap: 8,
            padding: '10px 12px', borderRadius: 'var(--radius-sm)',
            background: 'var(--canvas)', border: '1px solid var(--hairline)',
            cursor: 'pointer', textAlign: 'left' as const,
          }}
        >
          <Zap size={14} style={{ color: 'var(--accent)' }} />
          <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--ink)', flex: 1 }}>{t('plugin.hookTest')}</span>
          {expandedHook ? <ChevronUp size={14} style={{ color: 'var(--mute)' }} /> : <ChevronDown size={14} style={{ color: 'var(--mute)' }} />}
        </button>

        {expandedHook && (
          <div style={{
            marginTop: 6, padding: 12, borderRadius: 'var(--radius-sm)',
            background: 'var(--canvas)', border: '1px solid var(--hairline)',
          }}>
            <div style={{ marginBottom: 8 }}>
              <label style={{ fontSize: 11, color: 'var(--mute)', fontWeight: 500, marginBottom: 4, display: 'block' }}>
                {t('plugin.hookName')}
              </label>
              <input
                value={hookName}
                onChange={e => setHookName(e.target.value)}
                placeholder="on_document_loaded"
                style={{
                  width: '100%', height: 32, padding: '0 10px',
                  background: 'var(--canvas-soft)', border: '1px solid var(--hairline)',
                  borderRadius: 'var(--radius-sm)', color: 'var(--ink)', fontSize: 12,
                  outline: 'none', boxSizing: 'border-box' as const,
                }}
              />
            </div>
            <div style={{ marginBottom: 10 }}>
              <label style={{ fontSize: 11, color: 'var(--mute)', fontWeight: 500, marginBottom: 4, display: 'block' }}>
                {t('plugin.hookKwargs')}
              </label>
              <textarea
                value={hookKwargs}
                onChange={e => setHookKwargs(e.target.value)}
                rows={3}
                style={{
                  width: '100%', padding: '6px 10px',
                  background: 'var(--canvas-soft)', border: '1px solid var(--hairline)',
                  borderRadius: 'var(--radius-sm)', color: 'var(--ink)', fontSize: 11,
                  outline: 'none', fontFamily: 'monospace', resize: 'vertical' as const,
                  boxSizing: 'border-box' as const,
                }}
              />
            </div>
            <button
              onClick={handleTriggerHook}
              disabled={hookTriggering || !hookName.trim()}
              style={{
                padding: '6px 14px', borderRadius: 'var(--radius-sm)',
                background: 'var(--accent)', color: 'var(--on-primary)',
                border: 'none', cursor: hookTriggering ? 'wait' : 'pointer',
                fontSize: 12, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 5,
                opacity: hookTriggering || !hookName.trim() ? 0.6 : 1,
              }}
            >
              {hookTriggering ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
              {t('plugin.triggerHook')}
            </button>

            {hookError && (
              <div style={{
                marginTop: 10, padding: '6px 10px', borderRadius: 'var(--radius-sm)',
                background: 'var(--danger-soft)', color: 'var(--danger)', fontSize: 11,
                display: 'flex', alignItems: 'center', gap: 6,
              }}>
                <AlertTriangle size={12} /> {hookError}
              </div>
            )}

            {hookResults && (
              <div style={{ marginTop: 10 }}>
                <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 6 }}>
                  {t('plugin.handlersCalled')}: {hookResults.handlers_called}
                </div>
                {hookResults.results.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    {hookResults.results.map((hr, idx) => (
                      <div key={idx} style={{
                        padding: '8px 10px', borderRadius: 'var(--radius-sm)',
                        background: 'var(--canvas-soft)', border: '1px solid var(--hairline)',
                        fontSize: 11,
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                          {hr.success ? (
                            <CheckCircle2 size={12} style={{ color: 'var(--accent)' }} />
                          ) : (
                            <XCircle size={12} style={{ color: 'var(--danger)' }} />
                          )}
                          <span style={{ fontWeight: 500, color: 'var(--ink)' }}>{hr.plugin}</span>
                          <span style={{ color: 'var(--mute)', marginLeft: 'auto' }}>{hr.duration_ms}ms</span>
                        </div>
                        {hr.error && (
                          <div style={{ color: 'var(--danger)', fontSize: 10, marginTop: 2 }}>{hr.error}</div>
                        )}
                        {hr.result !== undefined && hr.result !== null && (
                          <pre style={{
                            margin: '4px 0 0', padding: '4px 6px', borderRadius: 'var(--radius-sm)',
                            background: 'var(--canvas)', fontSize: 10, color: 'var(--body)',
                            overflow: 'auto', maxHeight: 120,
                          }}>
                            {typeof hr.result === 'string' ? hr.result : JSON.stringify(hr.result, null, 2)}
                          </pre>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: 11, color: 'var(--mute)', textAlign: 'center', padding: 8 }}>
                    {t('plugin.noHandlers')}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
