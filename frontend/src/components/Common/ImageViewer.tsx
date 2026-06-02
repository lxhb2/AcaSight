import React, { useState, useEffect } from 'react';
import { ZoomIn, ZoomOut, RotateCw, Download } from 'lucide-react';

interface ImageViewerProps {
  url: string;
  fileName: string;
  fileType: 'image' | 'svg';
}

export const ImageViewer: React.FC<ImageViewerProps> = ({ url, fileName, fileType }) => {
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [svgHtml, setSvgHtml] = useState<string | null>(null);

  useEffect(() => {
    if (fileType === 'svg') {
      fetch(url)
        .then(r => r.text())
        .then(html => setSvgHtml(html))
        .catch(() => setSvgHtml(null));
    }
  }, [url, fileType]);

  const handleZoomIn = () => setZoom(z => Math.min(z + 0.25, 5));
  const handleZoomOut = () => setZoom(z => Math.max(z - 0.25, 0.25));
  const handleRotate = () => setRotation(r => (r + 90) % 360);
  const handleDownload = () => {
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    a.click();
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg-primary)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px', borderBottom: '1px solid var(--hairline)', background: 'var(--glass-bg)' }}>
        <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--body)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{fileName}</span>
        <button onClick={handleZoomOut} style={toolbarBtnStyle} title="缩小"><ZoomOut size={14} /></button>
        <span style={{ fontSize: 11, color: 'var(--mute)', minWidth: 36, textAlign: 'center' }}>{Math.round(zoom * 100)}%</span>
        <button onClick={handleZoomIn} style={toolbarBtnStyle} title="放大"><ZoomIn size={14} /></button>
        <button onClick={handleRotate} style={toolbarBtnStyle} title="旋转"><RotateCw size={14} /></button>
        <button onClick={handleDownload} style={toolbarBtnStyle} title="下载"><Download size={14} /></button>
      </div>
      <div style={{ flex: 1, overflow: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16, background: 'var(--canvas-soft)' }}>
        {fileType === 'svg' && svgHtml ? (
          <div
            style={{ transform: `scale(${zoom}) rotate(${rotation}deg)`, transformOrigin: 'center center', transition: 'transform 0.2s ease' }}
            dangerouslySetInnerHTML={{ __html: svgHtml }}
          />
        ) : (
          <img
            src={url}
            alt={fileName}
            style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', transform: `scale(${zoom}) rotate(${rotation}deg)`, transformOrigin: 'center center', transition: 'transform 0.2s ease' }}
          />
        )}
      </div>
    </div>
  );
};

const toolbarBtnStyle: React.CSSProperties = {
  padding: 4, borderRadius: 4, border: '1px solid var(--hairline)',
  background: 'transparent', color: 'var(--body)', cursor: 'pointer',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
};
