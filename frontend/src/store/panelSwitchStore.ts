/**
 * 面板切换 Store — 跨组件面板切换通信
 * 子组件可通过此 store 请求切换到指定面板，ObsidianLayout 消费请求并执行切换
 */

import { create } from 'zustand';

interface PanelSwitchState {
  /** 目标面板 ID */
  targetPanel: string | null;
  /** 请求切换到指定面板 */
  requestSwitch: (panelId: string) => void;
  /** 消费切换请求（读取后清空） */
  consumeSwitch: () => string | null;
}

export const usePanelSwitchStore = create<PanelSwitchState>((set, get) => ({
  targetPanel: null,
  requestSwitch: (panelId: string) => set({ targetPanel: panelId }),
  consumeSwitch: () => {
    const target = get().targetPanel;
    set({ targetPanel: null });
    return target;
  },
}));
