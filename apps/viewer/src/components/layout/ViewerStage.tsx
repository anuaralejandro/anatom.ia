import React, { useRef, useEffect, useCallback } from 'react';
import { useUIStore, uiActions } from '../../store/useUIStore';
import { CameraToolbar } from '../controls/CameraToolbar';
import { AxisNavigationGizmo } from '../controls/AxisNavigationGizmo';

export const ViewerStage: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const theme = useUIStore((s) => s.theme);
  const layoutMode = useUIStore((s) => s.layoutMode);
  const selectedId = useUIStore((s) => s.selectedId);
  const structures = useUIStore((s) => s.structures);

  const selected = structures.find((s) => s.id === selectedId);
  const isMobile = layoutMode === 'compact' || layoutMode === 'compact-wide';

  // Static / On-demand render function (Zero infinite loops - F09)
  const drawPreview = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const width = Math.floor(rect.width * dpr);
    const height = Math.floor(rect.height * dpr);

    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }

    ctx.save();
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;

    // Stage background
    ctx.fillStyle = theme === 'dark' ? '#03060B' : '#E9F0F3';
    ctx.fillRect(0, 0, w, h);

    // Subtle anatomical grid
    const gridColor = theme === 'dark' ? 'rgba(32, 45, 64, 0.3)' : 'rgba(220, 229, 236, 0.5)';
    ctx.strokeStyle = gridColor;
    ctx.lineWidth = 1;

    const gridSize = 40;
    for (let x = 0; x < w; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }
    for (let y = 0; y < h; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    // Static synthetic anatomical projection of pelvic ring & sacrum
    const centerX = w / 2;
    const centerY = h / 2;
    const radius = Math.min(w, h) * 0.28;

    ctx.translate(centerX, centerY);

    // Isometric Pelvic Ring static contours
    ctx.strokeStyle = theme === 'dark' ? '#58B9FF' : '#087A7A';
    ctx.lineWidth = 2;
    ctx.shadowColor = theme === 'dark' ? 'rgba(88, 185, 255, 0.4)' : 'rgba(8, 122, 122, 0.2)';
    ctx.shadowBlur = 12;

    // Draw stylized anatomical pelvis boundary
    ctx.beginPath();
    for (let i = 0; i <= 360; i += 5) {
      const rad = (i * Math.PI) / 180;
      const r = radius * (0.85 + 0.15 * Math.sin(rad * 2) + 0.1 * Math.cos(rad * 3));
      const px = r * Math.cos(rad);
      const py = r * Math.sin(rad) * 0.65;
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.stroke();

    // Sacrum central anchor
    ctx.fillStyle = theme === 'dark' ? 'rgba(88, 185, 255, 0.18)' : 'rgba(8, 122, 122, 0.15)';
    ctx.beginPath();
    ctx.ellipse(0, -radius * 0.2, radius * 0.22, radius * 0.35, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // Selected structure pin
    if (selected) {
      ctx.shadowBlur = 16;
      ctx.fillStyle = '#58B9FF';
      ctx.beginPath();
      ctx.arc(0, -radius * 0.2, 5, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.restore();
  }, [theme, selected]);

  // Render on-demand: on mount, resize or state change (Zero continuous loop)
  useEffect(() => {
    let resizeRaf = 0;
    const ro = new ResizeObserver(() => {
      cancelAnimationFrame(resizeRaf);
      resizeRaf = requestAnimationFrame(() => drawPreview());
    });

    if (canvasRef.current) {
      ro.observe(canvasRef.current);
    }

    drawPreview();

    return () => {
      cancelAnimationFrame(resizeRaf);
      ro.disconnect();
    };
  }, [drawPreview]);

  return (
    <main className="atlas-stage" aria-label="Visualizador anatómico 3D">
      <canvas
        ref={canvasRef}
        className="atlas-canvas"
        tabIndex={0}
        aria-label="Lienzo de renderizado anatómico (Vista conceptual M05-A)"
      />

      {/* Conceptual Banner required by M05-A */}
      <div className="atlas-conceptual-banner" role="status">
        <span className="atlas-conceptual-pill">M05-A.1</span>
        <span>Vista conceptual · Pelvis humana</span>
      </div>

      {/* F16: 3D Axis Navigation Gizmo (Blender style) in top-right */}
      <AxisNavigationGizmo
        size={isMobile ? 64 : 76}
        onSelectAxis={(axis) => {
          console.info(`[ViewerStage] Axis orientation selected: ${axis} (Enlace wgpu en M05-B)`);
        }}
      />

      {/* Camera Toolbar with clean Reset/Focus actions */}
      <CameraToolbar
        onResetCamera={() => {
          // Camera reset hook for M05-B
        }}
        onFocus={() => {
          if (selectedId) {
            uiActions.selectStructure(selectedId);
          }
        }}
      />
    </main>
  );
};
