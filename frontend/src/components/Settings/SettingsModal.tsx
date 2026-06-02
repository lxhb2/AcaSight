import React, { useState, useEffect, useCallback } from 'react';
import { useTheme } from '@/contexts/ThemeContext';
import { useTranslation } from 'react-i18next';
import { aiConfigApi } from '@/services/api';
import {
  Key, Palette, ChevronRight, Check, Sliders, Eye, EyeOff, X,
  Sun, Moon, Loader2, Save, Circle, Type, Lock,
  Zap, CheckCircle2, XCircle, AlertCircle, Globe,
} from 'lucide-react';

interface ProviderConfig {
  base_url: string;
  api_key: string;
  enabled: boolean;
  model?: string;
  has_api_key?: boolean;
}

interface AIConfig {
  default_provider: string;
  default_model: string;
  providers: Record<string, ProviderConfig>;
}

const PROVIDER_INFO: Record<string, {
  nameKey: string;
  descKey: string;
  needsKey: boolean;
  defaultUrl: string;
  icon: string;
  accentColor: string;
  models?: string[];
}> = {
  ollama: {
    nameKey: 'settings.providerOllama', descKey: 'settings.providerLocalModel', needsKey: false,
    defaultUrl: 'http://localhost:11434', icon: '🖥️', accentColor: 'var(--accent)',
    models: ['llama3', 'llama3.1', 'qwen2.5', 'codellama', 'mistral', 'phi3'],
  },
  openai: {
    nameKey: 'settings.providerOpenai', descKey: 'settings.providerOpenaiDesc', needsKey: true,
    defaultUrl: 'https://api.openai.com/v1', icon: '🤖', accentColor: '#50e3c2',
    models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
  },
  deepseek: {
    nameKey: 'settings.providerDeepseek', descKey: 'settings.providerDeepseekDesc', needsKey: true,
    defaultUrl: 'https://api.deepseek.com/v1', icon: '🔵', accentColor: 'var(--accent)',
    models: ['deepseek-chat', 'deepseek-coder', 'deepseek-reasoner'],
  },
  siliconflow: {
    nameKey: 'settings.providerSiliconflow', descKey: 'settings.providerSiliconflowDesc', needsKey: true,
    defaultUrl: 'https://api.siliconflow.cn/v1', icon: '💧', accentColor: 'var(--violet)',
    models: ['Qwen/Qwen2.5-7B-Instruct', 'Qwen/Qwen2.5-14B-Instruct', 'deepseek-ai/DeepSeek-V3', 'Pro/Qwen/Qwen2.5-7B-Instruct'],
  },
  minimax: {
    nameKey: 'settings.providerMinimax', descKey: 'settings.providerMinimaxDesc', needsKey: true,
    defaultUrl: 'https://api.minimax.chat/v1', icon: '🟠', accentColor: 'var(--warning)',
    models: ['abab6.5s-chat', 'abab6.5-chat', 'abab7-chat'],
  },
  glm: {
    nameKey: 'settings.providerGlm', descKey: 'settings.providerGlmDesc', needsKey: true,
    defaultUrl: 'https://open.bigmodel.cn/api/paas/v4', icon: '🟢', accentColor: 'var(--cyan)',
    models: ['glm-4-flash', 'glm-4-air', 'glm-4-plus', 'glm-4'],
  },
  claude: {
    nameKey: 'settings.providerClaude', descKey: 'settings.providerClaudeDesc', needsKey: true,
    defaultUrl: 'https://api.anthropic.com', icon: '🟡', accentColor: '#f9cb28',
    models: ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-3-opus-20240229'],
  },
};

const PROVIDER_ORDER = ['siliconflow', 'openai', 'deepseek', 'ollama', 'minimax', 'glm', 'claude'];

interface TestResult {
  connected: boolean;
  models?: string[];
  error?: string;
}

interface SettingsModalProps {
  onClose: () => void;
  showAI: boolean;
  onToggleAI: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ onClose, showAI, onToggleAI }) => {
  const { theme, setTheme, fontSize, setFontSize } = useTheme();
  const { t, i18n } = useTranslation();
  const [activeSection, setActiveSection] = useState<'ai' | 'appearance'>('ai');
  const [selectedProvider, setSelectedProvider] = useState<string>('siliconflow');

  const [config, setConfig] = useState<AIConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testingProvider, setTestingProvider] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({});
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [saveMsg, setSaveMsg] = useState('');

  useEffect(() => {
    const load = async () => {
      try {
        const c = await aiConfigApi.getConfig();
        setConfig(c);
        if (c.default_provider) setSelectedProvider(c.default_provider);
      } catch {} finally { setLoading(false); }
    };
    load();
  }, []);

  const updateProvider = useCallback((name: string, field: string, value: string | number | boolean) => {
    setConfig(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        providers: { ...prev.providers, [name]: { ...prev.providers[name], [field]: value } },
      };
    });
  }, []);

  const handleSave = useCallback(async () => {
    if (!config) return;
    setSaving(true);
    setSaveMsg('');
    try {
      const cleanProviders: Record<string, ProviderConfig> = {};
      for (const [pname, pconf] of Object.entries(config.providers)) {
        const { has_api_key, ...rest } = pconf;
        cleanProviders[pname] = rest as ProviderConfig;
      }
      await aiConfigApi.saveConfig({
        default_provider: config.default_provider,
        default_model: config.default_model,
        providers: cleanProviders,
      });
      setSaveMsg(t('settings.saveSuccess'));
      setTimeout(() => setSaveMsg(''), 3000);
    } catch {
      setSaveMsg(t('settings.saveFailed'));
    } finally { setSaving(false); }
  }, [config, t]);

  const handleTest = useCallback(async (provider: string) => {
    if (!config) return;
    setTestingProvider(provider);
    const pconf = config.providers[provider] || {};
    try {
      const res = await aiConfigApi.testProvider({
        provider,
        base_url: pconf.base_url || PROVIDER_INFO[provider]?.defaultUrl || '',
        api_key: pconf.api_key || '',
      });
      setTestResults(prev => ({ ...prev, [provider]: res }));
      if (res.models?.length) {
        const info = PROVIDER_INFO[provider];
        if (info) info.models = res.models;
      }
    } catch (e: unknown) {
      setTestResults(prev => ({ ...prev, [provider]: { connected: false, error: e instanceof Error ? e.message : String(e) } }));
    } finally { setTestingProvider(null); }
  }, [config]);

  const toggleShowKey = useCallback((name: string) => {
    setShowKeys(prev => ({ ...prev, [name]: !prev[name] }));
  }, []);

  const setDefaultProvider = (provider: string) => {
    setConfig(prev => prev ? { ...prev, default_provider: provider } : prev);
    setSelectedProvider(provider);
  };

  const renderAIConfig = () => {
    if (loading || !config) {
      return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, color: 'var(--mute)' }}>
          <Loader2 size={24} className="animate-spin" style={{ marginRight: 8 }} />
          {t('common.loading')}
        </div>
      );
    }

    const currentInfo = PROVIDER_INFO[selectedProvider] || PROVIDER_INFO['siliconflow'];
    const pconf = config.providers[selectedProvider] || { base_url: currentInfo.defaultUrl, api_key: '', enabled: false };
    const testRes = testResults[selectedProvider];
    const isTesting = testingProvider === selectedProvider;

    return (
      <div style={{ display: 'flex', height: 520, gap: 0 }}>
        <div style={{
          width: 200, flexShrink: 0, borderRight: '1px solid var(--hairline)',
          display: 'flex', flexDirection: 'column', overflow: 'hidden',
        }}>
          <div style={{ padding: '12px 10px 8px', borderBottom: '1px solid var(--hairline)' }}>
            <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 6 }}>{t('settings.selectProvider')}</div>
          </div>
          <div style={{ flex: 1, overflow: 'auto', padding: '6px' }}>
            {PROVIDER_ORDER.map(pid => {
              const info = PROVIDER_INFO[pid];
              const isSelected = selectedProvider === pid;
              const res = testResults[pid];
              const isDefault = config.default_provider === pid;
              const p = config.providers[pid];
              const hasKey = p?.api_key && p.api_key.length > 0;

              return (
                <button
                  key={pid}
                  onClick={() => setSelectedProvider(pid)}
                  style={{
                    width: '100%', display: 'flex', alignItems: 'center', gap: 8,
                    padding: '8px 8px', marginBottom: 2, borderRadius:'var(--radius-sm)',
                    background: isSelected ? 'var(--canvas-soft-2)' : 'transparent',
                    border: isSelected ? '1px solid var(--hairline)' : '1px solid transparent',
                    cursor: 'pointer', textAlign: 'left' as const,
                    transition: 'all 0.12s',
                  }}
                >
                  <span style={{ fontSize: 18 }}>{info.icon}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <span style={{ fontSize: 12, fontWeight: isSelected ? 600 : 400, color: 'var(--ink)', whiteSpace: 'nowrap' as const, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {t(info.nameKey)}
                      </span>
                      {isDefault && (
                        <span style={{ fontSize: 8, padding: '1px 4px', borderRadius:'var(--radius-sm)', background: 'var(--accent)', color: 'var(--on-primary)', flexShrink: 0 }}>{t('settings.defaultBadge')}</span>
                      )}
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--mute)', whiteSpace: 'nowrap' as const, overflow: 'hidden', textOverflow: 'ellipsis' }}>{t(info.descKey)}</div>
                  </div>
                  <div style={{ flexShrink: 0 }}>
                    {res ? (
                      res.connected ? (
                        <CheckCircle2 size={14} style={{ color: 'var(--accent)' }} />
                      ) : (
                        <XCircle size={14} style={{ color: 'var(--danger)' }} />
                      )
                    ) : hasKey ? (
                      <Circle size={10} style={{ fill: 'var(--mute)', color: 'var(--mute)', opacity: 0.5 }} />
                    ) : null}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <div style={{ flex: 1, overflow: 'auto', padding: '20px 24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
            <span style={{ fontSize: 32 }}>{currentInfo.icon}</span>
            <div>
              <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--ink)' }}>{t(currentInfo.nameKey)}</div>
              <div style={{ fontSize: 11, color: 'var(--mute)' }}>{t(currentInfo.descKey)}</div>
            </div>
            <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
              {testRes && (
                <span style={{
                  fontSize: 11, padding: '3px 10px', borderRadius:'var(--radius-sm)',
                  background: testRes.connected ? 'var(--accent-bg-soft)' : 'var(--danger-soft)',
                  color: testRes.connected ? 'var(--accent)' : 'var(--danger)',
                  display: 'flex', alignItems: 'center', gap: 4,
                }}>
                  {testRes.connected ? <CheckCircle2 size={11} /> : <XCircle size={11} />}
                  {testRes.connected ? t('settings.connected') : t('settings.connectionFailed')}
                </span>
              )}
              <button
                onClick={() => handleTest(selectedProvider)}
                disabled={isTesting}
                style={{
                  padding: '5px 14px', borderRadius:'var(--radius-sm)',
                  background: 'var(--accent)', color: 'var(--on-primary)',
                  border: 'none', cursor: isTesting ? 'wait' : 'pointer',
                  fontSize: 12, display: 'flex', alignItems: 'center', gap: 5,
                  opacity: isTesting ? 0.7 : 1, fontWeight: 500,
                }}
              >
                {isTesting ? <Loader2 size={11} className="animate-spin" /> : <Zap size={11} />}
                {isTesting ? t('settings.testing') : t('settings.testConnection')}
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div>
              <label style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 5, display: 'block', fontWeight: 500 }}>{t('settings.apiAddress')}</label>
              <input
                type="text"
                value={pconf.base_url || currentInfo.defaultUrl}
                onChange={e => updateProvider(selectedProvider, 'base_url', e.target.value)}
                placeholder={currentInfo.defaultUrl}
                style={{
                  width: '100%', height: 36,
                  background:'var(--canvas)', border: '1px solid var(--hairline)', borderRadius:'var(--radius-sm)',
                  padding: '0 12px', color: 'var(--ink)', fontSize: 12, outline: 'none',
                  transition: 'border-color 0.15s',
                }}
              />
            </div>

            {currentInfo.needsKey && (
              <div>
                <label style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 5, display: 'block', fontWeight: 500 }}>
                  API Key
                </label>
                <div style={{ display: 'flex', gap: 6 }}>
                  <div style={{ flex: 1, position: 'relative' }}>
                    <input
                      type={showKeys[selectedProvider] ? 'text' : 'password'}
                      value={pconf.api_key || ''}
                      onChange={e => updateProvider(selectedProvider, 'api_key', e.target.value)}
                      placeholder={pconf.has_api_key ? t('settings.apiKeyConfigured') : t('settings.apiKeyPlaceholder')}
                      style={{
                        width: '100%', height: 36,
                        background:'var(--canvas)', border: `1px solid ${pconf.has_api_key && !pconf.api_key ? 'var(--accent)' : 'var(--hairline)'}`,
                        borderRadius:'var(--radius-sm)',
                        padding: pconf.has_api_key && !pconf.api_key ? '0 40px 0 12px' : '0 12px',
                        color: 'var(--ink)', fontSize: 12, outline: 'none',
                      }}
                    />
                    {pconf.has_api_key && !pconf.api_key && (
                      <Lock size={14}
                        style={{
                          position: 'absolute', right: 12, top: 11,
                          color: 'var(--accent)', pointerEvents: 'none',
                        }}
                      />
                    )}
                  </div>
                  <button
                    onClick={() => toggleShowKey(selectedProvider)}
                    style={{
                      width: 36, height: 36, borderRadius:'var(--radius-sm)',
                      background:'var(--canvas)', border: '1px solid var(--hairline)',
                      color: 'var(--mute)', cursor: 'pointer',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}
                  >
                    {showKeys[selectedProvider] ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
                {pconf.has_api_key && !pconf.api_key && (
                  <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 'var(--radius-sm)', background: '#22c55e20', color: '#22c55e', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 3 }}>
                      <Lock size={10} /> {t('settings.keyConfigured')}
                    </span>
                    <span style={{ fontSize: 10, color: 'var(--mute)' }}>{t('settings.keyReplaceTip')}</span>
                  </div>
                )}
                {testRes?.error && (
                  <div style={{ marginTop: 6, fontSize: 10, color: 'var(--danger)', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <AlertCircle size={11} /> {testRes.error}
                  </div>
                )}
              </div>
            )}

            <div>
              <label style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 5, display: 'block', fontWeight: 500 }}>{t('settings.model')}</label>
              {testRes?.models && testRes.models.length > 0 ? (
                <select
                  value={pconf.model || testRes.models[0]}
                  onChange={e => updateProvider(selectedProvider, 'model', e.target.value)}
                  style={{
                    width: '100%', height: 36,
                    background:'var(--canvas)', border: '1px solid var(--hairline)', borderRadius:'var(--radius-sm)',
                    padding: '0 12px', color: 'var(--ink)', fontSize: 12, outline: 'none',
                  }}
                >
                  {testRes.models.map(m => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              ) : (
                <div>
                  <select
                    value={pconf.model || ''}
                    onChange={e => updateProvider(selectedProvider, 'model', e.target.value)}
                    style={{
                      width: '100%', height: 36,
                      background:'var(--canvas)', border: '1px solid var(--hairline)', borderRadius:'var(--radius-sm)',
                      padding: '0 12px', color: 'var(--ink)', fontSize: 12, outline: 'none',
                    }}
                  >
                    <option value="">{t('settings.autoSelect')}</option>
                    {(currentInfo.models || []).map(m => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                  <div style={{ marginTop: 5, fontSize: 10, color: 'var(--mute)', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <AlertCircle size={10} />
                    {t('settings.moreModelsTip')}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 24 }}>
            <button
              onClick={handleSave}
              disabled={saving}
              style={{
                padding: '8px 20px', borderRadius:'var(--radius-sm)', background: 'var(--surface-primary)', color: 'var(--on-primary)',
                border: 'none', cursor: saving ? 'wait' : 'pointer', fontSize: 13, fontWeight: 500,
                display: 'flex', alignItems: 'center', gap: 6,
                opacity: saving ? 0.7 : 1,
              }}
            >
              {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
              {t('common.save')}
            </button>
            {saveMsg && (
              <span style={{ fontSize: 12, color: saveMsg.includes('✓') ? 'var(--accent)' : 'var(--danger)' }}>{saveMsg}</span>
            )}
          </div>

          {config.default_provider !== selectedProvider && (
            <div style={{ marginTop: 16, padding: '10px 14px', borderRadius:'var(--radius-sm)', background:'var(--accent-bg-soft)', border: '1px solid var(--hairline)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--ink)' }}>{t('settings.setDefaultService')}</div>
                  <div style={{ fontSize: 10, color: 'var(--mute)' }}>{t('settings.setDefaultDesc')}</div>
                </div>
                <button
                  onClick={() => setDefaultProvider(selectedProvider)}
                  style={{
                    padding: '5px 14px', borderRadius:'var(--radius-sm)',
                    background: 'var(--accent)', color: 'var(--on-primary)', border: 'none',
                    cursor: 'pointer', fontSize: 11, fontWeight: 500,
                  }}
                >
                  {t('settings.setDefault')}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderAppearanceSection = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 480 }}>
      <div>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--ink)', display: 'flex', alignItems: 'center', gap: 6 }}>
          <Sun size={15} /> {t('settings.themeMode')}
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          {[
            { id: 'light' as const, nameKey: 'settings.lightTheme', descKey: 'settings.lightThemeDesc', icon: Sun },
            { id: 'dark' as const, nameKey: 'settings.darkTheme', descKey: 'settings.darkThemeDesc', icon: Moon },
          ].map(themeOpt => (
            <button key={themeOpt.id} onClick={() => setTheme(themeOpt.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: 14, borderRadius:'var(--radius-sm)',
                border: `1px solid ${theme === themeOpt.id ? 'var(--accent)' : 'var(--hairline)'}`,
                background: theme === themeOpt.id ? 'var(--accent-bg-soft)' : 'var(--canvas-soft)',
                color: theme === themeOpt.id ? 'var(--accent)' : 'var(--body)',
                cursor: 'pointer', transition: 'all 0.15s', textAlign: 'left' as const,
              }}>
              <themeOpt.icon size={22} />
              <div>
                <div style={{ fontWeight: 600, fontSize: 13 }}>{t(themeOpt.nameKey)}</div>
                <div style={{ fontSize: 10, color: 'var(--mute)' }}>{t(themeOpt.descKey)}</div>
              </div>
              {theme === themeOpt.id && <Check size={14} style={{ marginLeft: 'auto' }} />}
            </button>
          ))}
        </div>
      </div>

      <div>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--ink)', display: 'flex', alignItems: 'center', gap: 6 }}>
          <Globe size={15} /> {t('common.language')}
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          {[
            { id: 'zh', name: '中文', desc: '简体中文', icon: '🇨🇳' },
            { id: 'en', name: 'English', desc: 'US English', icon: '🇺🇸' },
          ].map(l => (
            <button key={l.id} onClick={() => i18n.changeLanguage(l.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: 14, borderRadius:'var(--radius-sm)',
                border: `1px solid ${i18n.language === l.id ? 'var(--accent)' : 'var(--hairline)'}`,
                background: i18n.language === l.id ? 'var(--accent-bg-soft)' : 'var(--canvas-soft)',
                color: i18n.language === l.id ? 'var(--accent)' : 'var(--body)',
                cursor: 'pointer', transition: 'all 0.15s', textAlign: 'left' as const,
              }}>
              <span style={{ fontSize: 22 }}>{l.icon}</span>
              <div>
                <div style={{ fontWeight: 600, fontSize: 13 }}>{l.name}</div>
                <div style={{ fontSize: 10, color: 'var(--mute)' }}>{l.desc}</div>
              </div>
              {i18n.language === l.id && <Check size={14} style={{ marginLeft: 'auto' }} />}
            </button>
          ))}
        </div>
      </div>

      <div>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--ink)', display: 'flex', alignItems: 'center', gap: 6 }}>
          <Type size={15} /> {t('settings.fontSize')}
        </h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px', borderRadius:'var(--radius-sm)', background:'var(--accent-bg-soft)', border: '1px solid var(--hairline)' }}>
          <span style={{ fontSize: 11, color: 'var(--mute)' }}>A</span>
          <input
            type="range" min={10} max={24} step={1}
            value={fontSize}
            onChange={e => setFontSize(parseInt(e.target.value, 10))}
            style={{ flex: 1, accentColor: 'var(--accent)', height: 4 }}
          />
          <span style={{ fontSize: 16, fontWeight: 600, color: 'var(--ink)', width: 40, textAlign: 'center' }}>{fontSize}</span>
        </div>
      </div>

      <div>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--ink)', display: 'flex', alignItems: 'center', gap: 6 }}>
          <Sliders size={15} /> {t('settings.layoutTitle')}
        </h3>
        <div style={{ padding: 12, borderRadius:'var(--radius-sm)', background:'var(--accent-bg-soft)', border: '1px solid var(--hairline)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--ink)' }}>{t('settings.aiChatPanel')}</div>
            <div style={{ fontSize: 10, color: 'var(--mute)' }}>{t('settings.aiChatPanelDesc')}</div>
          </div>
          <button
            onClick={onToggleAI}
            style={{
              position: 'relative', width: 44, height: 24,
              background: showAI ? 'var(--accent)' : 'var(--hairline)',
              borderRadius:'var(--radius-sm)', border: 'none', cursor: 'pointer', transition: '0.2s',
            }}
          >
            <span style={{
              position: 'absolute', top: 2, left: showAI ? 21 : 2,
              width: 20, height: 20, backgroundColor: 'var(--canvas)', borderRadius: '50%',
              transition: '0.2s',
            }} />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 100, display: 'flex',
      alignItems: 'center', justifyContent: 'center',
      background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(8px)',
    }} onClick={onClose}>
      <div style={{
        width: activeSection === 'ai' ? 800 : 560, maxHeight: '88vh', borderRadius:'var(--radius-lg)',
        background: 'var(--glass-bg)', border: '1px solid var(--glass-border)',
        backdropFilter: 'blur(var(--glass-blur))', WebkitBackdropFilter: 'blur(var(--glass-blur))',
        boxShadow: 'var(--glass-shadow)', display: 'flex', overflow: 'hidden',
        transition: 'width 0.2s ease',
      }} onClick={e => e.stopPropagation()}>
        <div style={{ width: 160, padding: '16px 10px', borderRight: '1px solid var(--glass-border)', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
            <h2 style={{ fontSize: 15, fontWeight: 600, color: 'var(--ink)' }}>{t('settings.title')}</h2>
            <button onClick={onClose}
              style={{ width: 24, height: 24, borderRadius:'var(--radius-sm)', background: 'transparent', border: 'none', color: 'var(--mute)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <X size={13} />
            </button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {[
              { id: 'ai' as const, icon: Key, labelKey: 'settings.aiModel' },
              { id: 'appearance' as const, icon: Palette, labelKey: 'settings.appearance' },
            ].map(s => (
              <button key={s.id} onClick={() => setActiveSection(s.id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px', borderRadius:'var(--radius-sm)',
                  background: activeSection === s.id ? 'var(--canvas-soft-2)' : 'transparent',
                  color: activeSection === s.id ? 'var(--ink)' : 'var(--body)',
                  border: 'none', cursor: 'pointer', fontSize: 12, width: '100%', textAlign: 'left' as const,
                  fontWeight: activeSection === s.id ? 600 : 400,
                  transition: 'all 0.1s',
                }}>
                <s.icon size={14} />
                <span style={{ flex: 1 }}>{t(s.labelKey)}</span>
                <ChevronRight size={10} style={{ opacity: 0.4 }} />
              </button>
            ))}
          </div>
        </div>

        <div style={{ flex: 1, overflow: 'auto' }}>
          {activeSection === 'ai' && (
            <div style={{ padding: '0' }}>
              <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--hairline)', display: 'flex', alignItems: 'center', gap: 8 }}>
                <Key size={15} style={{ color: 'var(--accent)' }} />
                <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink)' }}>{t('settings.aiConfigTitle')}</span>
                <span style={{ marginLeft: 6, fontSize: 10, color: 'var(--mute)', background:'var(--accent-bg-soft)', padding: '2px 8px', borderRadius:'var(--radius-sm)' }}>
                  {PROVIDER_INFO[config?.default_provider || 'siliconflow']?.icon} {t(PROVIDER_INFO[config?.default_provider || 'siliconflow']?.nameKey || '')}
                </span>
              </div>
              {renderAIConfig()}
            </div>
          )}
          {activeSection === 'appearance' && (
            <div style={{ padding: 20 }}>
              <div style={{ padding: '0 0 16px', borderBottom: '1px solid var(--hairline)', marginBottom: 4 }}>
                <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Palette size={14} style={{ color: 'var(--accent)' }} /> {t('settings.appearanceTitle')}
                </span>
              </div>
              {renderAppearanceSection()}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
