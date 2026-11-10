/**
 * ANATOM.IA — BRIDGE NORMALIZER
 * Safe transform functions converting Rust/WASM outputs to camelCase TypeScript.
 */

import type {
  RustSceneSnapshot,
  NormalizedSceneSnapshot,
  RustEngineCapabilities,
  NormalizedEngineCapabilities,
  RustMemoryStats,
  NormalizedMemoryStats,
  EngineEvent,
} from './bridge-types';

export function normalizeSceneSnapshot(raw: unknown): NormalizedSceneSnapshot {
  if (!raw || typeof raw !== 'object') {
    return {
      selectedId: null,
      sceneRevision: 0,
      visibleIds: [],
      region: '',
      variant: '',
      quality: 'medium',
      backend: 'unknown',
    };
  }

  const r = raw as RustSceneSnapshot;
  const backend = r.backend === 'webgpu' || r.backend === 'webgl2' ? r.backend : 'unknown';

  return {
    selectedId: typeof r.selected_id === 'string' ? r.selected_id : null,
    sceneRevision: typeof r.scene_revision === 'number' ? r.scene_revision : 0,
    visibleIds: Array.isArray(r.visible_ids) ? r.visible_ids : [],
    region: typeof r.region === 'string' ? r.region : '',
    variant: typeof r.variant === 'string' ? r.variant : '',
    quality: typeof r.quality === 'string' ? r.quality : 'medium',
    backend,
  };
}

export function normalizeCapabilities(raw: unknown): NormalizedEngineCapabilities {
  if (!raw || typeof raw !== 'object') {
    return {
      adapterName: 'Unknown Adapter',
      backendType: 'Unknown',
      maxTextureDimension2D: 2048,
      supportsTimestamps: false,
    };
  }

  const r = raw as RustEngineCapabilities;
  return {
    adapterName: typeof r.adapter_name === 'string' ? r.adapter_name : 'Default Adapter',
    backendType: typeof r.backend_type === 'string' ? r.backend_type : 'WebGL2',
    maxTextureDimension2D: typeof r.max_texture_dimension_2d === 'number' ? r.max_texture_dimension_2d : 2048,
    supportsTimestamps: Boolean(r.supports_timestamps),
  };
}

export function normalizeMemoryStats(raw: unknown): NormalizedMemoryStats {
  if (!raw || typeof raw !== 'object') {
    return {
      residentGpuBytes: 0,
      cpuDecodedBytes: 0,
      peakGpuBytes: 0,
      budgetBytes: 0,
    };
  }

  const r = raw as RustMemoryStats;
  return {
    residentGpuBytes: typeof r.resident_gpu_bytes === 'number' ? r.resident_gpu_bytes : 0,
    cpuDecodedBytes: typeof r.cpu_decoded_bytes === 'number' ? r.cpu_decoded_bytes : 0,
    peakGpuBytes: typeof r.peak_gpu_bytes === 'number' ? r.peak_gpu_bytes : 0,
    budgetBytes: typeof r.budget_bytes === 'number' ? r.budget_bytes : 0,
  };
}

export function normalizeEvent(raw: unknown): EngineEvent {
  if (!raw || typeof raw !== 'object') {
    return { type: 'unknown' };
  }

  const r = raw as Record<string, unknown>;
  return {
    type: typeof r.type === 'string' ? r.type : 'unknown',
    requestId: typeof r.requestId === 'number' ? r.requestId : (typeof r.request_id === 'number' ? r.request_id : undefined),
    sceneGeneration: typeof r.sceneGeneration === 'number' ? r.sceneGeneration : (typeof r.scene_generation === 'number' ? r.scene_generation : undefined),
    sceneRevision: typeof r.sceneRevision === 'number' ? r.sceneRevision : (typeof r.scene_revision === 'number' ? r.scene_revision : undefined),
    region: typeof r.region === 'string' ? r.region : undefined,
    variant: typeof r.variant === 'string' ? r.variant : undefined,
    lod: typeof r.lod === 'number' ? r.lod : undefined,
    backend: typeof r.backend === 'string' ? r.backend : undefined,
    timestamp: typeof r.timestamp === 'number' ? r.timestamp : undefined,
    error: typeof r.error === 'string' ? r.error : undefined,
    errorCode: typeof r.errorCode === 'string' ? r.errorCode : (typeof r.error_code === 'string' ? r.error_code : undefined),
  };
}
