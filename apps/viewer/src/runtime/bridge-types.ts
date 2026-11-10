/**
 * ANATOM.IA — RUNTIME BRIDGE TYPES & INTERFACES
 * Normalizes Rust/WASM snake_case contracts into strict TypeScript camelCase.
 */

export interface RustSceneSnapshot {
  selected_id?: string | null;
  scene_revision?: number;
  visible_ids?: string[];
  region?: string;
  variant?: string;
  quality?: string;
  backend?: string;
}

export interface RustEngineCapabilities {
  adapter_name?: string;
  backend_type?: string;
  max_texture_dimension_2d?: number;
  supports_timestamps?: boolean;
}

export interface RustMemoryStats {
  resident_gpu_bytes?: number;
  cpu_decoded_bytes?: number;
  peak_gpu_bytes?: number;
  budget_bytes?: number;
}

export interface NormalizedSceneSnapshot {
  selectedId: string | null;
  sceneRevision: number;
  visibleIds: string[];
  region: string;
  variant: string;
  quality: string;
  backend: 'webgpu' | 'webgl2' | 'unknown';
}

export interface NormalizedEngineCapabilities {
  adapterName: string;
  backendType: string;
  maxTextureDimension2D: number;
  supportsTimestamps: boolean;
}

export interface NormalizedMemoryStats {
  residentGpuBytes: number;
  cpuDecodedBytes: number;
  peakGpuBytes: number;
  budgetBytes: number;
}

export interface EngineEvent {
  type: string;
  requestId?: number;
  sceneGeneration?: number;
  sceneRevision?: number;
  region?: string;
  variant?: string;
  lod?: number;
  backend?: string;
  timestamp?: number;
  error?: string;
  errorCode?: string;
}

export interface AnatomyLabels {
  es: string;
  en: string;
  la: string;
}

export interface AnatomyStructure {
  id: string;
  ta2Id: string;
  system: string;
  labels: AnatomyLabels;
  side?: 'left' | 'right' | 'median' | 'bilateral' | 'unpaired_or_unspecified';
  category: 'bone' | 'joint' | 'muscle' | 'organ' | 'vascular' | 'nervous' | 'unclassified';
  visible?: boolean;
}

export type QualityProfile = 'low' | 'medium' | 'high';
export type ThemeMode = 'dark' | 'light';
export type LayoutMode = 'compact' | 'compact-wide' | 'tablet' | 'workstation' | 'pro-wide';
export type SheetSnap = 'collapsed' | 'mid' | 'expanded';
export type ActiveOverlay = 'none' | 'explorer' | 'inspector' | 'settings';
export type CameraPreset = 'anterior' | 'posterior' | 'left' | 'right' | 'superior' | 'inferior';
