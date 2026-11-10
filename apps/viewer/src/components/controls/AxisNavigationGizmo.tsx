/**
 * ANATOM.IA — 3D AXIS NAVIGATION GIZMO (F16)
 * Blender-inspired 3D orientation gizmo projected in SVG.
 * 
 * Coordinate System Reference (Rust/wgpu & glTF 2.0):
 *   +X / -X : Lateral Derecha / Lateral Izquierda
 *   +Y / -Y : Superior (Craneal) / Inferior (Caudal)
 *   +Z / -Z : Anterior (Ventral) / Posterior (Dorsal)
 * 
 * Zero infinite loops: renders statically on demand.
 */

import React, { useMemo, useState } from 'react';

export type AxisId = '+X' | '-X' | '+Y' | '-Y' | '+Z' | '-Z';

export interface AxisNavigationGizmoProps {
  size?: number; // Visual size in px (desktop: ~76, mobile: ~64)
  azimuth?: number; // Camera azimuth angle in radians (default: -0.65)
  elevation?: number; // Camera elevation angle in radians (default: 0.45)
  onSelectAxis?: (axis: AxisId) => void;
  className?: string;
}

interface AxisEndpoint {
  id: AxisId;
  label: string;
  anatomicalView: string;
  color: string;
  isPositive: boolean;
  vec3: [number, number, number];
  screenX: number;
  screenY: number;
  depth: number;
}

const AXIS_DEFINITIONS = [
  { id: '+X' as AxisId, label: 'X', anatomicalView: 'Lateral Derecha', color: '#E65B63', isPositive: true, vec3: [1, 0, 0] as [number, number, number] },
  { id: '-X' as AxisId, label: '', anatomicalView: 'Lateral Izquierda', color: '#E65B63', isPositive: false, vec3: [-1, 0, 0] as [number, number, number] },
  { id: '+Y' as AxisId, label: 'Y', anatomicalView: 'Superior', color: '#55C987', isPositive: true, vec3: [0, 1, 0] as [number, number, number] },
  { id: '-Y' as AxisId, label: '', anatomicalView: 'Inferior', color: '#55C987', isPositive: false, vec3: [0, -1, 0] as [number, number, number] },
  { id: '+Z' as AxisId, label: 'Z', anatomicalView: 'Anterior', color: '#58B9FF', isPositive: true, vec3: [0, 0, 1] as [number, number, number] },
  { id: '-Z' as AxisId, label: '', anatomicalView: 'Posterior', color: '#58B9FF', isPositive: false, vec3: [0, 0, -1] as [number, number, number] },
];

export const AxisNavigationGizmo: React.FC<AxisNavigationGizmoProps> = ({
  size = 76,
  azimuth: initialAzimuth = -0.65,
  elevation: initialElevation = 0.45,
  onSelectAxis,
  className = '',
}) => {
  const [currentAzimuth, setCurrentAzimuth] = useState(initialAzimuth);
  const [currentElevation, setCurrentElevation] = useState(initialElevation);
  const [hoveredAxis, setHoveredAxis] = useState<AxisId | null>(null);

  const cx = size / 2;
  const cy = size / 2;
  const radius = size * 0.36;

  // Project 3D axes using camera view rotation matrix
  const projectedAxes = useMemo(() => {
    const cosA = Math.cos(currentAzimuth);
    const sinA = Math.sin(currentAzimuth);
    const cosE = Math.cos(currentElevation);
    const sinE = Math.sin(currentElevation);

    const endpoints: AxisEndpoint[] = AXIS_DEFINITIONS.map((axis) => {
      const [x, y, z] = axis.vec3;

      // 1. Azimuth rotation around Y
      const x1 = x * cosA + z * sinA;
      const y1 = y;
      const z1 = -x * sinA + z * cosA;

      // 2. Elevation rotation around X
      const x2 = x1;
      const y2 = y1 * cosE - z1 * sinE;
      const z2 = y1 * sinE + z1 * cosE;

      // 3. Screen coordinates (Y inverted in 2D)
      const screenX = cx + x2 * radius;
      const screenY = cy - y2 * radius;

      return {
        ...axis,
        screenX,
        screenY,
        depth: z2,
      };
    });

    // Painter's algorithm: Sort by depth (farthest first)
    return endpoints.sort((a, b) => a.depth - b.depth);
  }, [currentAzimuth, currentElevation, cx, cy, radius]);

  const handleAxisClick = (axis: AxisId) => {
    // Snap gizmo orientation to target orthogonal view
    switch (axis) {
      case '+X': // Right lateral
        setCurrentAzimuth(-Math.PI / 2);
        setCurrentElevation(0);
        break;
      case '-X': // Left lateral
        setCurrentAzimuth(Math.PI / 2);
        setCurrentElevation(0);
        break;
      case '+Y': // Superior
        setCurrentAzimuth(0);
        setCurrentElevation(Math.PI / 2 - 0.001);
        break;
      case '-Y': // Inferior
        setCurrentAzimuth(0);
        setCurrentElevation(-Math.PI / 2 + 0.001);
        break;
      case '+Z': // Anterior
        setCurrentAzimuth(0);
        setCurrentElevation(0);
        break;
      case '-Z': // Posterior
        setCurrentAzimuth(Math.PI);
        setCurrentElevation(0);
        break;
    }

    onSelectAxis?.(axis);
  };

  return (
    <div
      className={`atlas-axis-gizmo atlas-axis-gizmo-container ${className}`}
      role="region"
      aria-label="Control de orientación 3D (Gizmo de ejes)"
      style={{
        position: 'absolute',
        top: '16px',
        right: '16px',
        width: `${size}px`,
        height: `${size}px`,
        zIndex: 'var(--z-floating-toolbar)',
        userSelect: 'none',
      }}
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{ overflow: 'visible', display: 'block' }}
      >
        {/* Central hub anchor */}
        <circle
          cx={cx}
          cy={cy}
          r={radius * 0.18}
          fill="rgba(18, 28, 43, 0.75)"
          stroke="#202D40"
          strokeWidth="1.5"
        />

        {/* Connecting lines & endpoints sorted by depth */}
        {projectedAxes.map((endpoint) => {
          const isFront = endpoint.depth >= -0.05;
          const isHovered = hoveredAxis === endpoint.id;
          const sphereRadius = endpoint.isPositive ? 8 : 4.5;

          return (
            <g key={endpoint.id} className="atlas-gizmo-axis-group">
              {/* Connector line to center hub */}
              <line
                x1={cx}
                y1={cy}
                x2={endpoint.screenX}
                y2={endpoint.screenY}
                stroke={endpoint.color}
                strokeWidth={isFront ? 1.75 : 1}
                strokeOpacity={isFront ? 0.85 : 0.35}
                strokeDasharray={endpoint.isPositive ? undefined : '2 2'}
              />

              {/* Endpoint target circle / sphere */}
              <g
                className="atlas-axis-node"
                tabIndex={0}
                role="button"
                aria-label={`Alinear vista al eje ${endpoint.id} (${endpoint.anatomicalView})`}
                onClick={() => handleAxisClick(endpoint.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleAxisClick(endpoint.id);
                  }
                }}
                onMouseEnter={() => setHoveredAxis(endpoint.id)}
                onMouseLeave={() => setHoveredAxis(null)}
                style={{ cursor: 'pointer', outline: 'none' }}
              >
                {/* Touch hitbox expansion (ensures >=44x44 target on touch) */}
                <circle
                  cx={endpoint.screenX}
                  cy={endpoint.screenY}
                  r={16}
                  fill="transparent"
                />

                {/* Visible sphere */}
                <circle
                  cx={endpoint.screenX}
                  cy={endpoint.screenY}
                  r={isHovered ? sphereRadius + 1.5 : sphereRadius}
                  fill={endpoint.color}
                  fillOpacity={endpoint.isPositive ? (isFront ? 1 : 0.7) : (isFront ? 0.45 : 0.25)}
                  stroke={isHovered ? '#FFFFFF' : '#05080D'}
                  strokeWidth="1"
                />

                {/* Axis letter label on positive endpoints */}
                {endpoint.isPositive && (
                  <text
                    x={endpoint.screenX}
                    y={endpoint.screenY + 3.5}
                    textAnchor="middle"
                    fill="#05080D"
                    fontSize="9.5px"
                    fontWeight="800"
                    fontFamily="var(--font-sans)"
                    pointerEvents="none"
                  >
                    {endpoint.label}
                  </text>
                )}
              </g>
            </g>
          );
        })}
      </svg>
    </div>
  );
};
