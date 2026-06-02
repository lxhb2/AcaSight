import { describe, it, expect } from 'vitest';
import type { OutlineNode } from '@/services/api';

function findNodeByKey(nodes: OutlineNode[], key: string): OutlineNode | null {
  const parts = key.split('.').map(Number);
  let current: OutlineNode[] = nodes;
  let node: OutlineNode | null = null;
  for (const part of parts) {
    if (!current || part >= current.length) return null;
    node = current[part];
    current = node?.sections || [];
  }
  return node;
}

const sampleOutline: OutlineNode[] = [
  {
    level: 1,
    title: 'Introduction',
    estimated_words: 500,
    sections: [
      { level: 2, title: 'Background', sections: [] },
      { level: 2, title: 'Motivation', sections: [] },
    ],
  },
  {
    level: 1,
    title: 'Methods',
    estimated_words: 2000,
    sections: [
      {
        level: 2,
        title: 'Data Collection',
        sections: [
          { level: 3, title: 'Dataset', sections: [] },
        ],
      },
    ],
  },
  {
    level: 1,
    title: 'Conclusion',
    sections: [],
  },
];

describe('findNodeByKey', () => {
  it('should find top-level node by single index', () => {
    const node = findNodeByKey(sampleOutline, '0');
    expect(node).not.toBeNull();
    expect(node!.title).toBe('Introduction');
  });

  it('should find second top-level node', () => {
    const node = findNodeByKey(sampleOutline, '1');
    expect(node!.title).toBe('Methods');
  });

  it('should find nested child node', () => {
    const node = findNodeByKey(sampleOutline, '0.1');
    expect(node!.title).toBe('Motivation');
  });

  it('should find deeply nested node', () => {
    const node = findNodeByKey(sampleOutline, '1.0.0');
    expect(node!.title).toBe('Dataset');
  });

  it('should return null for out-of-bounds index', () => {
    expect(findNodeByKey(sampleOutline, '5')).toBeNull();
  });

  it('should return null for out-of-bounds nested index', () => {
    expect(findNodeByKey(sampleOutline, '0.5')).toBeNull();
  });

  it('should return first node for empty string key (Number("") === 0)', () => {
    const node = findNodeByKey(sampleOutline, '');
    expect(node).not.toBeNull();
    expect(node!.title).toBe('Introduction');
  });

  it('should find node without sections', () => {
    const node = findNodeByKey(sampleOutline, '2');
    expect(node!.title).toBe('Conclusion');
    expect(node!.sections).toEqual([]);
  });
});

describe('OutlineNode structure', () => {
  it('should support recursive sections', () => {
    const deep: OutlineNode = {
      level: 1,
      title: 'Root',
      sections: [
        {
          level: 2,
          title: 'Child',
          sections: [
            { level: 3, title: 'Grandchild', sections: [] },
          ],
        },
      ],
    };
    expect(deep.sections![0].sections![0].title).toBe('Grandchild');
  });

  it('should have optional fields', () => {
    const minimal: OutlineNode = { level: 1, title: 'Minimal' };
    expect(minimal.sections).toBeUndefined();
    expect(minimal.estimated_words).toBeUndefined();
    expect(minimal.description).toBeUndefined();
  });
});
