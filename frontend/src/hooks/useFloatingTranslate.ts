/**
 * useFloatingTranslate — 浮动翻译高级功能 Hook
 *
 * 提供 AI 解释功能
 */

import { useState, useCallback } from 'react';
import { aiApi } from '../services/api';

export function useFloatingTranslate() {
  const [aiExplanation, setAiExplanation] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [showAiExplanation, setShowAiExplanation] = useState(false);

  const generateExplanation = useCallback(async (text: string) => {
    setShowAiExplanation(true);
    setAiLoading(true);
    setAiExplanation('');

    try {
      const resp = await aiApi.chat(
        [
          {
            role: 'system',
            content: '你是一个学术助手。用中文简要解释以下英文文本的含义，包括关键术语和上下文。保持简洁（2-3句话）。',
          },
          { role: 'user', content: text },
        ],
        undefined,
        undefined,
      );
      setAiExplanation(resp.response);
    } catch (e) {
      setAiExplanation('AI 解释生成失败: ' + (e as Error).message);
    } finally {
      setAiLoading(false);
    }
  }, []);

  return {
    aiExplanation,
    aiLoading,
    showAiExplanation,
    setShowAiExplanation,
    generateExplanation,
  };
}