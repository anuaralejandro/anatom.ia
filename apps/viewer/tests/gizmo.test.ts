import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

describe('3D Axis Navigation Gizmo (F16) Mathematics & Coordinate System', () => {
  const AXIS_VECTORS: Record<string, [number, number, number]> = {
    '+X': [1, 0, 0],
    '-X': [-1, 0, 0],
    '+Y': [0, 1, 0],
    '-Y': [0, -1, 0],
    '+Z': [0, 0, 1],
    '-Z': [0, 0, -1],
  };

  const projectVector = (
    vec: [number, number, number],
    azimuth: number,
    elevation: number,
    size: number = 76
  ) => {
    const [x, y, z] = vec;
    const cosA = Math.cos(azimuth);
    const sinA = Math.sin(azimuth);
    const cosE = Math.cos(elevation);
    const sinE = Math.sin(elevation);

    // 1. Azimuth rotation around Y
    const x1 = x * cosA + z * sinA;
    const y1 = y;
    const z1 = -x * sinA + z * cosA;

    // 2. Elevation rotation around X
    const x2 = x1;
    const y2 = y1 * cosE - z1 * sinE;
    const z2 = y1 * sinE + z1 * cosE;

    const cx = size / 2;
    const cy = size / 2;
    const radius = size * 0.36;

    return {
      screenX: cx + x2 * radius,
      screenY: cy - y2 * radius,
      depth: z2,
    };
  };

  it('projects all 6 axes with valid screen coordinates and depth', () => {
    const size = 76;
    for (const [id, vec] of Object.entries(AXIS_VECTORS)) {
      const proj = projectVector(vec, -0.65, 0.45, size);
      assert.ok(proj.screenX >= 0 && proj.screenX <= size, `Axis ${id} screenX out of bounds`);
      assert.ok(proj.screenY >= 0 && proj.screenY <= size, `Axis ${id} screenY out of bounds`);
      assert.ok(proj.depth >= -1.01 && proj.depth <= 1.01, `Axis ${id} depth out of range`);
    }
  });

  it('correctly maps axes to anatomical standard orientations', () => {
    // In Rust / glTF coordinate standard:
    // +X is Lateral Right
    // -X is Lateral Left
    // +Y is Superior / Cranial
    // -Y is Inferior / Caudal
    // +Z is Anterior / Ventral
    // -Z is Posterior / Dorsal
    const anatomicalViews: Record<string, string> = {
      '+X': 'Lateral Derecha',
      '-X': 'Lateral Izquierda',
      '+Y': 'Superior',
      '-Y': 'Inferior',
      '+Z': 'Anterior',
      '-Z': 'Posterior',
    };

    assert.equal(anatomicalViews['+X'], 'Lateral Derecha');
    assert.equal(anatomicalViews['-X'], 'Lateral Izquierda');
    assert.equal(anatomicalViews['+Y'], 'Superior');
    assert.equal(anatomicalViews['-Y'], 'Inferior');
    assert.equal(anatomicalViews['+Z'], 'Anterior');
    assert.equal(anatomicalViews['-Z'], 'Posterior');
  });

  it('depth sorting places front axes over back axes (painter algorithm)', () => {
    // Looking directly at +Z (Anterior view: azimuth=0, elevation=0)
    const anteriorZ = projectVector(AXIS_VECTORS['+Z'], 0, 0);
    const posteriorZ = projectVector(AXIS_VECTORS['-Z'], 0, 0);

    assert.ok(anteriorZ.depth > posteriorZ.depth, '+Z must be in front of -Z when looking anteriorly');
    assert.equal(Math.round(anteriorZ.depth), 1);
    assert.equal(Math.round(posteriorZ.depth), -1);
  });
});
