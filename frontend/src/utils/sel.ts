export interface Point {
  x: number;
  y: number;
}

export interface Rect {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

export interface Position {
  point: Point;
  dir: 'up' | 'down';
}

export interface TextSelection {
  text: string;
  page: number;
  rect?: Rect;
  range?: Range;
  annotated?: boolean;
  /** When set, this selection represents an existing annotation being edited. */
  annotationId?: string;
}

/**
 * Check if a point is inside a rectangle (with padding).
 */
export const isPointInRect = (point: Point, rect: Rect, padding = 1): boolean => {
  return (
    point.x >= rect.left + padding &&
    point.x <= rect.right - padding &&
    point.y >= rect.top + padding &&
    point.y <= rect.bottom - padding
  );
};

/**
 * Check if a pointer event is inside the current selection.
 */
export const isPointerInsideSelection = (selection: Selection, ev: PointerEvent): boolean => {
  if (selection.rangeCount === 0) return false;
  const range = selection.getRangeAt(0);
  const rects = range.getClientRects();
  const padding = 20;
  for (let i = 0; i < rects.length; i++) {
    const rect = rects[i]!;
    if (
      ev.clientX >= rect.left - padding &&
      ev.clientX <= rect.right + padding &&
      ev.clientY >= rect.top - padding &&
      ev.clientY <= rect.bottom + padding
    ) {
      return true;
    }
  }
  return false;
};

/**
 * Get the best position for a popup above/below a selection range.
 * Returns a Position with point and direction (up/down).
 * Adapted from Readest's getPosition.
 */
export const getPopupAnchor = (
  range: Range,
  containerRect: Rect,
  paddingPx = 10,
): Position | null => {
  const rects = Array.from(range.getClientRects());
  if (rects.length === 0) return null;

  const first = rects[0]!;
  const last = rects.at(-1)!;

  // Position ABOVE selection (preferred)
  const upPoint: Point = {
    x: (first.left + first.right) / 2 - containerRect.left,
    y: first.top - containerRect.top - 10,
  };
  // Position BELOW selection (fallback)
  const downPoint: Point = {
    x: (last.left + last.right) / 2 - containerRect.left,
    y: last.bottom - containerRect.top + 6,
  };

  // Constrain within container
  const constrainX = (x: number) => Math.max(paddingPx, Math.min(x, containerRect.right - containerRect.left - paddingPx));
  const constrainY = (y: number) => Math.max(paddingPx, Math.min(y, containerRect.bottom - containerRect.top - paddingPx));

  // Prefer up if visible
  if (upPoint.y > paddingPx) {
    return { point: { x: constrainX(upPoint.x), y: constrainY(upPoint.y) }, dir: 'up' };
  }
  return { point: { x: constrainX(downPoint.x), y: constrainY(downPoint.y) }, dir: 'down' };
};

/**
 * Get the full bounding rect of a selection range.
 */
export const getRangeRect = (range: Range): Rect | null => {
  const rect = range.getBoundingClientRect();
  if (rect.width === 0 && rect.height === 0) return null;
  return {
    top: rect.top,
    right: rect.right,
    bottom: rect.bottom,
    left: rect.left,
  };
};

/**
 * Snap a range to whole word boundaries using Intl.Segmenter.
 */
export const snapRangeToWords = (range: Range): void => {
  if (typeof Intl === 'undefined' || !Intl.Segmenter) return;

  const isPunctuation = (ch: string) => /^\p{P}|\p{S}$/u.test(ch);

  // Snap start to word start
  const snapStart = () => {
    const node = range.startContainer;
    if (node.nodeType !== Node.TEXT_NODE) return;
    const text = node.textContent ?? '';
    const offset = range.startOffset;
    if (offset === 0 || offset >= text.length) return;
    const charAtOffset = text[offset] ?? '';
    if (isPunctuation(charAtOffset)) return;

    const segmenter = new Intl.Segmenter(undefined, { granularity: 'word' });
    for (const seg of segmenter.segment(text)) {
      if (seg.isWordLike && seg.index < offset && seg.index + seg.segment.length > offset) {
        range.setStart(node, seg.index);
        break;
      }
    }
  };

  // Snap end to word end
  const snapEnd = () => {
    const node = range.endContainer;
    if (node.nodeType !== Node.TEXT_NODE) return;
    const text = node.textContent ?? '';
    const offset = range.endOffset;
    if (offset === 0 || offset >= text.length) return;
    const charBeforeOffset = text[offset - 1] ?? '';
    if (isPunctuation(charBeforeOffset)) return;

    const segmenter = new Intl.Segmenter(undefined, { granularity: 'word' });
    for (const seg of segmenter.segment(text)) {
      if (seg.isWordLike && seg.index < offset && seg.index + seg.segment.length > offset) {
        range.setEnd(node, seg.index + seg.segment.length);
        break;
      }
    }
  };

  snapStart();
  snapEnd();
};

/**
 * Get clean text from a range, handling pdf.js BR elements.
 * In pdf.js TextLayer, <br role="presentation"> separates lines.
 * Without this, multiline selections collapse words together.
 */
export const getTextFromRange = (range: Range): string => {
  const clonedRange = range.cloneRange();
  const fragment = clonedRange.cloneContents();
  const walker = document.createTreeWalker(
    fragment,
    NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT,
    null,
  );

  let text = '';
  let node: Node | null;
  while ((node = walker.nextNode())) {
    if (node.nodeType === Node.TEXT_NODE) {
      text += (node as Text).nodeValue ?? '';
    } else if ((node as Element).tagName === 'BR') {
      text += '\n';
    }
  }
  return text;
};

// ============================================================================
// Popup positioning (借鉴 Readest 的 getPosition / getPopupPosition)
// ============================================================================

/**
 * Constrain a point within a rect with a padding.
 */
const constrainPoint = (point: Point, rect: Rect, padding: number): Point => {
  return {
    x: Math.max(padding, Math.min(point.x, rect.right - rect.left - padding)),
    y: Math.max(padding, Math.min(point.y, rect.bottom - rect.top - padding)),
  };
};

const pointIsInView = ({ x, y }: Point) =>
  x > 0 && y > 0 && x < window.innerWidth && y < window.innerHeight;

/**
 * Compute the triangle anchor position for a popup attached to a selection.
 *
 * Returns a position above (`up`) or below (`down`) the selection range
 * relative to the container rect, plus a hint about which side has more
 * room. When the range is split across multiple lines the first/last
 * client rects are used.
 *
 * A point at (0, 0) signals "no good position" — callers should treat
 * it as "don't show the popup".
 */
export const getPosition = (
  range: Range,
  containerRect: Rect,
  paddingPx = 10,
): Position => {
  const rects = Array.from(range.getClientRects());
  if (rects.length === 0) return { point: { x: 0, y: 0 }, dir: 'up' };

  const first = rects[0]!;
  const last = rects.at(-1)!;

  // Convert viewport-relative rects to container-relative points
  const offsetLeft = containerRect.left;
  const offsetTop = containerRect.top;

  const upPoint: Point = {
    x: (first.left + first.right) / 2 - offsetLeft,
    y: first.top - offsetTop - 12,
  };
  const downPoint: Point = {
    x: (last.left + last.right) / 2 - offsetLeft,
    y: last.bottom - offsetTop + 6,
  };

  const upC = constrainPoint(upPoint, containerRect, paddingPx);
  const downC = constrainPoint(downPoint, containerRect, paddingPx);

  // Prefer above; fall back to below when above is not visible.
  if (upC.y > paddingPx && upC.y < containerRect.bottom - containerRect.top - paddingPx) {
    return { point: upC, dir: 'up' };
  }
  if (downC.y > paddingPx && downC.y < containerRect.bottom - containerRect.top - paddingPx) {
    return { point: downC, dir: 'down' };
  }
  // Last resort: return the one closer to viewport.
  if (upC.y > 0) return { point: upC, dir: 'up' };
  return { point: downC, dir: 'down' };
};

/**
 * Position a popup so its centre aligns with the triangle anchor
 * and it stays inside the bounding container (with padding).
 */
export const getPopupPosition = (
  anchor: Position,
  containerRect: Rect,
  popupW: number,
  popupH: number,
  paddingPx = 10,
): Position => {
  let x = 0;
  let y = 0;
  if (anchor.dir === 'up') {
    x = anchor.point.x - popupW / 2;
    y = anchor.point.y - popupH;
  } else {
    x = anchor.point.x - popupW / 2;
    y = anchor.point.y + 6;
  }

  const maxX = containerRect.right - containerRect.left - popupW - paddingPx;
  const maxY = containerRect.bottom - containerRect.top - popupH - paddingPx;
  x = Math.max(paddingPx, Math.min(x, maxX));
  y = Math.max(paddingPx, Math.min(y, maxY));

  return { point: { x, y }, dir: anchor.dir };
};

/** True when the anchor point is actually inside the viewport. */
export const isAnchorInView = (pos: Position): boolean => pointIsInView(pos.point);