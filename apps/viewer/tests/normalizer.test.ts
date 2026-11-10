import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  normalizeSceneSnapshot,
  normalizeCapabilities,
  normalizeMemoryStats,
  normalizeEvent,
} from '../src/runtime/normalizer';

describe('Bridge Normalizer Suite', () => {
  it('converts Rust snake_case SceneSnapshot into camelCase NormalizedSceneSnapshot', () => {
    const raw = {
      selected_id: 'ta2:1071',
      scene_revision: 5,
      visible_ids: ['ta2:1071', 'ta2:1092'],
      region: 'pelvis',
      variant: 'male-adult',
      quality: 'high',
      backend: 'webgpu',
    };

    const normalized = normalizeSceneSnapshot(raw);
    assert.equal(normalized.selectedId, 'ta2:1071');
    assert.equal(normalized.sceneRevision, 5);
    assert.deepEqual(normalized.visibleIds, ['ta2:1071', 'ta2:1092']);
    assert.equal(normalized.region, 'pelvis');
    assert.equal(normalized.variant, 'male-adult');
    assert.equal(normalized.quality, 'high');
    assert.equal(normalized.backend, 'webgpu');
  });

  it('handles null, empty or corrupt raw snapshots gracefully', () => {
    const fallback = normalizeSceneSnapshot(null);
    assert.equal(fallback.selectedId, null);
    assert.equal(fallback.sceneRevision, 0);
    assert.deepEqual(fallback.visibleIds, []);
    assert.equal(fallback.backend, 'unknown');
  });

  it('converts EngineCapabilities snake_case into camelCase', () => {
    const raw = {
      adapter_name: 'NVIDIA RTX 4080',
      backend_type: 'WebGPU',
      max_texture_dimension_2d: 16384,
      supports_timestamps: true,
    };

    const caps = normalizeCapabilities(raw);
    assert.equal(caps.adapterName, 'NVIDIA RTX 4080');
    assert.equal(caps.backendType, 'WebGPU');
    assert.equal(caps.maxTextureDimension2D, 16384);
    assert.equal(caps.supportsTimestamps, true);
  });

  it('converts MemoryStats with high watermark and budget accounting', () => {
    const raw = {
      resident_gpu_bytes: 5242880,
      cpu_decoded_bytes: 1048576,
      peak_gpu_bytes: 8388608,
      budget_bytes: 134217728,
    };

    const mem = normalizeMemoryStats(raw);
    assert.equal(mem.residentGpuBytes, 5242880);
    assert.equal(mem.cpuDecodedBytes, 1048576);
    assert.equal(mem.peakGpuBytes, 8388608);
    assert.equal(mem.budgetBytes, 134217728);
  });

  it('normalizes engine events and prevents reentrancy metadata loss', () => {
    const raw = {
      type: 'region.ready',
      request_id: 42,
      scene_generation: 7,
      scene_revision: 7,
      region: 'pelvis',
      variant: 'male-adult',
      lod: 1,
      backend: 'webgpu',
      timestamp: 123.45,
    };

    const evt = normalizeEvent(raw);
    assert.equal(evt.type, 'region.ready');
    assert.equal(evt.requestId, 42);
    assert.equal(evt.sceneGeneration, 7);
    assert.equal(evt.sceneRevision, 7);
    assert.equal(evt.backend, 'webgpu');
    assert.equal(evt.timestamp, 123.45);
  });
});
