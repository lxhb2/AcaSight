/**
 * BookmarksView — 书签面板
 */

import React from 'react';
import { useApp } from '@/contexts/AppContext';

export const BookmarksView: React.FC = () => {
  const { openFile } = useApp();

  const bookmarks = [
    { name: 'Attention Is All You Need', type: 'pdf' as const },
    { name: 'Transformer 阅读笔记', type: 'md' as const },
    { name: 'ResNet 残差学习', type: 'pdf' as const },
    { name: 'LLaMA 训练技术报告', type: 'pdf' as const },
  ];

  return (
    <div className="acasight-outline-container">
      {bookmarks.map((b, i) => (
        <div key={i} className={`acasight-outline-item acasight-outline-h1 ${i === 0 ? 'active' : ''}`} onClick={() => openFile(b.name + (b.type === 'pdf' ? '.pdf' : '.md'), b.type)}>
          {b.name}
        </div>
      ))}
    </div>
  );
};
