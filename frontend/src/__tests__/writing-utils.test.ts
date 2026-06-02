import { describe, it, expect } from 'vitest';
import type { OutlineNode } from '@/services/api';

const findNodeByKey = (nodes: OutlineNode[], key: string): OutlineNode | null => {
  const parts = key.split('.').map(Number);
  let current: OutlineNode[] = nodes;
  let node: OutlineNode | null = null;
  for (const part of parts) {
    if (!current || part >= current.length) return null;
    node = current[part];
    current = node?.sections || [];
  }
  return node;
};

function updateNodeInTree(
  nodes: OutlineNode[],
  key: string,
  updater: (node: OutlineNode) => OutlineNode,
): OutlineNode[] {
  const parts = key.split('.').map(Number);
  function recurse(items: OutlineNode[], depth: number): OutlineNode[] {
    if (depth >= parts.length) return items;
    const idx = parts[depth];
    return items.map((item, i) => {
      if (i !== idx) return item;
      if (depth === parts.length - 1) return updater(item);
      return { ...item, sections: recurse(item.sections || [], depth + 1) };
    });
  }
  return recurse(nodes, 0);
}

function countWords(nodes: OutlineNode[]): number {
  return nodes.reduce((sum, n) => {
    return sum + (n.estimated_words || 0) + countWords(n.sections || []);
  }, 0);
}

const sampleOutline: OutlineNode[] = [
  {
    level: 1, title: 'Introduction', estimated_words: 500,
    sections: [
      { level: 2, title: 'Background', estimated_words: 200, sections: [] },
      { level: 2, title: 'Motivation', estimated_words: 300, sections: [] },
    ],
  },
  {
    level: 1, title: 'Methods', estimated_words: 2000,
    sections: [
      { level: 2, title: 'Data Collection', estimated_words: 800, sections: [] },
      { level: 2, title: 'Analysis', estimated_words: 1200, sections: [] },
    ],
  },
];

describe('WritingWorkspace - findNodeByKey', () => {
  it('should find top-level node', () => {
    expect(findNodeByKey(sampleOutline, '0')!.title).toBe('Introduction');
    expect(findNodeByKey(sampleOutline, '1')!.title).toBe('Methods');
  });

  it('should find nested node', () => {
    expect(findNodeByKey(sampleOutline, '0.1')!.title).toBe('Motivation');
    expect(findNodeByKey(sampleOutline, '1.0')!.title).toBe('Data Collection');
  });

  it('should return null for out-of-bounds', () => {
    expect(findNodeByKey(sampleOutline, '5')).toBeNull();
    expect(findNodeByKey(sampleOutline, '0.5')).toBeNull();
  });
});

describe('WritingWorkspace - updateNodeInTree', () => {
  it('should update a top-level node title', () => {
    const updated = updateNodeInTree(sampleOutline, '0', n => ({ ...n, title: 'Intro (updated)' }));
    expect(updated[0].title).toBe('Intro (updated)');
    expect(updated[1].title).toBe('Methods');
  });

  it('should update a nested node', () => {
    const updated = updateNodeInTree(sampleOutline, '1.0', n => ({ ...n, estimated_words: 1000 }));
    expect(updated[1].sections![0].estimated_words).toBe(1000);
  });

  it('should not mutate original', () => {
    const original = JSON.parse(JSON.stringify(sampleOutline));
    updateNodeInTree(sampleOutline, '0', n => ({ ...n, title: 'Changed' }));
    expect(sampleOutline).toEqual(original);
  });

  it('should preserve siblings when updating', () => {
    const updated = updateNodeInTree(sampleOutline, '0.0', n => ({ ...n, title: 'New Background' }));
    expect(updated[0].sections![0].title).toBe('New Background');
    expect(updated[0].sections![1].title).toBe('Motivation');
  });
});

describe('WritingWorkspace - countWords', () => {
  it('should sum all estimated_words recursively', () => {
    expect(countWords(sampleOutline)).toBe(500 + 200 + 300 + 2000 + 800 + 1200);
  });

  it('should handle nodes without estimated_words', () => {
    const nodes: OutlineNode[] = [
      { level: 1, title: 'A', sections: [{ level: 2, title: 'B', sections: [] }] },
    ];
    expect(countWords(nodes)).toBe(0);
  });

  it('should handle empty array', () => {
    expect(countWords([])).toBe(0);
  });
});
