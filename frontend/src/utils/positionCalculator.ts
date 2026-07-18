/**
 * positionCalculator — 弹窗定位计算器
 *
 * 借鉴 STranslate 的弹窗定位逻辑：
 * - 基于选区所有 DOMRect 计算最佳弹窗位置
 * - 默认在选区上方显示（空间不足时改下方）
 * - 视口边界检测与自动调整
 * - 支持 PDF 缩放因子
 */

export interface Position {
  top: number;
  left: number;
  visible: boolean;
}

export interface PositionOptions {
  popoverWidth?: number;
  popoverHeight?: number;
  gap?: number;
  scale?: number;
}

/**
 * 计算翻译弹窗位置（基于选区矩形）
 */
export function calculatePopoverPosition(
  rects: DOMRect[],
  options: PositionOptions = {},
): Position {
  const {
    popoverWidth = 380,
    popoverHeight = 300,
    gap = 8,
    scale = 1,
  } = options;

  if (!rects || rects.length === 0) {
    return { top: 0, left: 0, visible: false };
  }

  // 找到最上方的矩形
  const firstRect = rects.reduce((min, rect) => {
    if (rect.top < min.top || (rect.top === min.top && rect.left < min.left)) {
      return rect;
    }
    return min;
  }, rects[0]);

  // 默认在选区上方
  let top = firstRect.top - popoverHeight - gap;
  let left = firstRect.left + (firstRect.width * scale) / 2;

  // 视口边界检测
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;

  // 水平边界
  let adjustedLeft = left - popoverWidth / 2;
  if (adjustedLeft < gap) {
    adjustedLeft = gap;
  } else if (adjustedLeft + popoverWidth > viewportWidth - gap) {
    adjustedLeft = viewportWidth - popoverWidth - gap;
  }

  // 垂直边界：上方空间不足时改在下方
  let adjustedTop = top;
  if (adjustedTop < gap) {
    const lastRect = rects[rects.length - 1];
    adjustedTop = lastRect.bottom + gap;
  }

  // 确保不超出底部
  if (adjustedTop + popoverHeight > viewportHeight - gap) {
    adjustedTop = viewportHeight - popoverHeight - gap;
  }

  return {
    top: adjustedTop,
    left: adjustedLeft + popoverWidth / 2,
    visible: true,
  };
}

/**
 * 计算工具栏位置（更紧凑，高度约 40px）
 */
export function calculateToolbarPosition(
  rects: DOMRect[],
  options: PositionOptions = {},
): Position {
  const { popoverWidth = 220, gap = 8, scale = 1 } = options;

  if (!rects || rects.length === 0) {
    return { top: 0, left: 0, visible: false };
  }

  const firstRect = rects.reduce((min, rect) => {
    if (rect.top < min.top || (rect.top === min.top && rect.left < min.left)) {
      return rect;
    }
    return min;
  }, rects[0]);

  // 工具栏在选区上方，高度约 40px
  const toolbarHeight = 40;
  let top = firstRect.top - toolbarHeight - gap;
  let left = firstRect.left + (firstRect.width * scale) / 2;

  const viewportWidth = window.innerWidth;

  let adjustedLeft = left - popoverWidth / 2;
  if (adjustedLeft < gap) adjustedLeft = gap;
  if (adjustedLeft + popoverWidth > viewportWidth - gap) {
    adjustedLeft = viewportWidth - popoverWidth - gap;
  }

  let adjustedTop = top;
  if (adjustedTop < gap) {
    const lastRect = rects[rects.length - 1];
    adjustedTop = lastRect.bottom + gap;
  }

  return {
    top: adjustedTop,
    left: adjustedLeft + popoverWidth / 2,
    visible: true,
  };
}