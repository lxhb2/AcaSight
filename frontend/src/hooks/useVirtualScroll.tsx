import React, { useRef, useCallback } from 'react';
import { FixedSizeList as List } from 'react-window';
import AutoSizer from 'react-virtualized-auto-sizer';

interface VirtualListProps<T> {
  items: T[];
  itemHeight: number;
  overscan?: number;
  renderItem: (item: T, index: number) => React.ReactNode;
  className?: string;
  emptyContent?: React.ReactNode;
}

function VirtualListInner<T>({
  items,
  itemHeight,
  overscan = 5,
  renderItem,
  className,
  emptyContent,
}: VirtualListProps<T>) {
  if (items.length === 0) {
    return emptyContent ? <>{emptyContent}</> : null;
  }

  const Row = useCallback(
    ({ index, style }: { index: number; style: React.CSSProperties }) => (
      <div style={style}>{renderItem(items[index], index)}</div>
    ),
    [items, renderItem],
  );

  return (
    <div className={className} style={{ flex: 1, minHeight: 0 }}>
      <AutoSizer>
        {({ height, width }: { height: number; width: number }) => (
          <List
            height={height}
            width={width}
            itemCount={items.length}
            itemSize={itemHeight}
            overscanCount={overscan}
          >
            {Row}
          </List>
        )}
      </AutoSizer>
    </div>
  );
}

export const VirtualList = React.memo(VirtualListInner) as <T>(
  props: VirtualListProps<T>,
) => React.ReactElement | null;

interface UseVirtualScrollOptions {
  threshold?: number;
}

export function useVirtualScroll(options: UseVirtualScrollOptions = {}) {
  const { threshold = 50 } = options;
  const containerRef = useRef<HTMLDivElement>(null);

  const shouldVirtualize = useCallback(
    (itemCount: number) => itemCount >= threshold,
    [threshold],
  );

  return { containerRef, shouldVirtualize, VirtualList };
}
