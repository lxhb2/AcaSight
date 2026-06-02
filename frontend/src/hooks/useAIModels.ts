import { useState, useCallback, useEffect } from 'react';
import { aiConfigApi } from '@/services/api';

interface AIConfig {
  default_provider: string;
  default_model: string;
  providers: Record<string, {
    base_url: string;
    api_key: string;
    enabled: boolean;
    model?: string;
  }>;
}

interface ModelInfo {
  id: string;
  label: string;
}

/**
 * 共享 Hook: 获取 AI 配置和可用模型列表
 * 供 WritingPanel / AISidePanel / ChartPanel 等面板使用
 */
export function useAIModels() {
  const [config, setConfig] = useState<AIConfig | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [currentModel, setCurrentModel] = useState<string>('');
  const [loading, setLoading] = useState(false);

  // 加载配置
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const c = await aiConfigApi.getConfig();
        if (!mounted) return;
        setConfig(c);
        const provider = c.default_provider;
        const pconf = c.providers?.[provider];
        setCurrentModel(pconf?.model || c.default_model || '');
      } catch {
        // 配置加载失败，使用默认值
      }
    })();
    return () => { mounted = false; };
  }, []);

  // 获取当前 provider 的模型列表
  const refreshModels = useCallback(async (provider?: string) => {
    const p = provider || config?.default_provider || 'siliconflow';
    setLoading(true);
    try {
      const res = await aiConfigApi.getModels(p);
      const modelList = (res.models || []).map((id: string) => ({
        id,
        label: id.split('/').pop() || id, // 简化显示名
      }));
      setModels(modelList);
      return modelList;
    } catch {
      return [];
    } finally {
      setLoading(false);
    }
  }, [config]);

  // 切换模型
  const selectModel = useCallback(async (modelId: string) => {
    setCurrentModel(modelId);
    // 保存到后端
    try {
      const provider = config?.default_provider || 'siliconflow';
      const pconf = config?.providers?.[provider];
      if (pconf) {
        await aiConfigApi.saveConfig({
          providers: {
            [provider]: { ...pconf, model: modelId },
          },
        });
      }
    } catch {
      // 保存失败不影响使用
    }
  }, [config]);

  // 获取当前 provider 名
  const providerName = config?.default_provider || 'siliconflow';

  return {
    config,
    models,
    currentModel,
    loading,
    providerName,
    refreshModels,
    selectModel,
  };
}
