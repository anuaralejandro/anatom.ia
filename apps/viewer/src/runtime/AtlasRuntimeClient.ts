/**
 * ANATOM.IA — ATLAS RUNTIME CLIENT
 * Manages engine lifecycle, wasm loading, microtask event decoupling, and request generation.
 */

import {
  normalizeSceneSnapshot,
  normalizeCapabilities,
  normalizeMemoryStats,
  normalizeEvent,
} from './normalizer';
import type {
  NormalizedSceneSnapshot,
  NormalizedEngineCapabilities,
  NormalizedMemoryStats,
  EngineEvent,
  QualityProfile,
} from './bridge-types';

export type EventListener = (event: EngineEvent) => void;

export interface AtlasEngineLike {
  initialize(canvas: HTMLCanvasElement, options: unknown): Promise<unknown>;
  renderFrame(): boolean;
  requestRender(): void;
  resize(w: number, h: number): void;
  orbit(dx: number, dy: number): void;
  pan(dx: number, dy: number): void;
  zoom(delta: number): void;
  resetCamera(): number;
  setCameraPreset(presetId: number): void;
  selectStructure(id?: string | null): number;
  selectAt(xCss: number, yCss: number): string | undefined;
  isolateStructure(id: string): number;
  setVisibility(id: string, visible: boolean): number;
  resetVisibility(): number;
  setQualityProfile(profile: string): unknown;
  setTheme(dark: boolean): void;
  getSceneSnapshot(): unknown;
  getCapabilities(): unknown;
  getMemoryStats(): unknown;
  setEventCallback(cb: (event: unknown) => void): void;
  dispose(): void;
}

export class AtlasRuntimeClient {
  private engine: AtlasEngineLike | null = null;
  private canvas: HTMLCanvasElement | null = null;
  private listeners = new Set<EventListener>();
  private disposed = false;
  private currentRequestId = 0;
  private currentSceneGeneration = 0;

  // Cached state to prevent redundant queries
  private lastSnapshot: NormalizedSceneSnapshot = {
    selectedId: null,
    sceneRevision: 0,
    visibleIds: [],
    region: 'pelvis',
    variant: 'male-adult',
    quality: 'medium',
    backend: 'webgpu',
  };

  private lastCapabilities: NormalizedEngineCapabilities = {
    adapterName: 'Mock/Synthetic Engine',
    backendType: 'WebGPU',
    maxTextureDimension2D: 8192,
    supportsTimestamps: true,
  };

  private lastMemory: NormalizedMemoryStats = {
    residentGpuBytes: 0,
    cpuDecodedBytes: 0,
    peakGpuBytes: 0,
    budgetBytes: 134217728,
  };

  constructor(engineInstance?: AtlasEngineLike) {
    if (engineInstance) {
      this.attachEngine(engineInstance);
    }
  }

  public attachEngine(engine: AtlasEngineLike): void {
    if (this.disposed) return;
    this.engine = engine;

    // Critical: Microtask queue to avoid re-entrancy into Rust RefCell
    this.engine.setEventCallback((rawEvent: unknown) => {
      queueMicrotask(() => {
        if (this.disposed) return;
        const normalized = normalizeEvent(rawEvent);
        this.dispatch(normalized);
      });
    });
  }

  public addEventListener(listener: EventListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private dispatch(event: EngineEvent): void {
    for (const listener of this.listeners) {
      try {
        listener(event);
      } catch (err) {
        console.error('[AtlasRuntimeClient] Error in event listener:', err);
      }
    }
  }

  public async initCanvas(canvas: HTMLCanvasElement, preferredBackend: 'webgpu' | 'webgl2' = 'webgpu'): Promise<boolean> {
    if (this.disposed) return false;
    this.canvas = canvas;

    if (this.engine) {
      try {
        await this.engine.initialize(canvas, { backend: preferredBackend });
        this.syncState();
        return true;
      } catch (err) {
        console.warn('[AtlasRuntimeClient] Engine initialization deferred or failed:', err);
        return false;
      }
    }
    return false;
  }

  public syncState(): void {
    if (!this.engine || this.disposed) return;
    try {
      this.lastSnapshot = normalizeSceneSnapshot(this.engine.getSceneSnapshot());
      this.lastCapabilities = normalizeCapabilities(this.engine.getCapabilities());
      this.lastMemory = normalizeMemoryStats(this.engine.getMemoryStats());
    } catch {
      // Non-fatal if snapshot query is deferred
    }
  }

  public getCanvas(): HTMLCanvasElement | null {
    return this.canvas;
  }

  public getSnapshot(): NormalizedSceneSnapshot {
    return this.lastSnapshot;
  }

  public getCapabilities(): NormalizedEngineCapabilities {
    return this.lastCapabilities;
  }

  public getMemoryStats(): NormalizedMemoryStats {
    return this.lastMemory;
  }

  public nextRequestId(): number {
    return ++this.currentRequestId;
  }

  public nextGeneration(): number {
    return ++this.currentSceneGeneration;
  }

  public selectStructure(id: string | null): void {
    this.lastSnapshot = {
      ...this.lastSnapshot,
      selectedId: id,
      sceneRevision: this.lastSnapshot.sceneRevision + 1,
    };

    if (this.engine && !this.disposed) {
      try {
        this.engine.selectStructure(id);
      } catch (err) {
        console.warn('[AtlasRuntimeClient] selectStructure failed:', err);
      }
    }

    this.dispatch({
      type: 'structure.selected',
      requestId: this.currentRequestId,
      sceneRevision: this.lastSnapshot.sceneRevision,
    });
  }

  public setVisibility(id: string, visible: boolean): void {
    const current = new Set(this.lastSnapshot.visibleIds);
    if (visible) {
      current.add(id);
    } else {
      current.delete(id);
    }

    this.lastSnapshot = {
      ...this.lastSnapshot,
      visibleIds: Array.from(current),
      sceneRevision: this.lastSnapshot.sceneRevision + 1,
    };

    if (this.engine && !this.disposed) {
      try {
        this.engine.setVisibility(id, visible);
      } catch (err) {
        console.warn('[AtlasRuntimeClient] setVisibility failed:', err);
      }
    }

    this.dispatch({
      type: 'scene.changed',
      sceneRevision: this.lastSnapshot.sceneRevision,
    });
  }

  public isolateStructure(id: string): void {
    this.lastSnapshot = {
      ...this.lastSnapshot,
      selectedId: id,
      visibleIds: [id],
      sceneRevision: this.lastSnapshot.sceneRevision + 1,
    };

    if (this.engine && !this.disposed) {
      try {
        this.engine.isolateStructure(id);
      } catch (err) {
        console.warn('[AtlasRuntimeClient] isolateStructure failed:', err);
      }
    }

    this.dispatch({
      type: 'scene.changed',
      sceneRevision: this.lastSnapshot.sceneRevision,
    });
  }

  public resetVisibility(): void {
    if (this.engine && !this.disposed) {
      try {
        this.engine.resetVisibility();
      } catch (err) {
        console.warn('[AtlasRuntimeClient] resetVisibility failed:', err);
      }
    }

    this.dispatch({
      type: 'scene.changed',
      sceneRevision: this.lastSnapshot.sceneRevision + 1,
    });
  }

  public resetCamera(): void {
    if (this.engine && !this.disposed) {
      try {
        this.engine.resetCamera();
      } catch (err) {
        console.warn('[AtlasRuntimeClient] resetCamera failed:', err);
      }
    }
  }

  public setCameraPreset(presetId: number): void {
    if (this.engine && !this.disposed) {
      try {
        this.engine.setCameraPreset(presetId);
      } catch (err) {
        console.warn('[AtlasRuntimeClient] setCameraPreset failed:', err);
      }
    }
  }

  public setQualityProfile(profile: QualityProfile): void {
    this.lastSnapshot = {
      ...this.lastSnapshot,
      quality: profile,
    };

    if (this.engine && !this.disposed) {
      try {
        this.engine.setQualityProfile(profile);
      } catch (err) {
        console.warn('[AtlasRuntimeClient] setQualityProfile failed:', err);
      }
    }
  }

  public setTheme(dark: boolean): void {
    if (this.engine && !this.disposed) {
      try {
        this.engine.setTheme(dark);
      } catch (err) {
        console.warn('[AtlasRuntimeClient] setTheme failed:', err);
      }
    }
  }

  public resize(widthCss: number, heightCss: number): void {
    if (this.engine && !this.disposed) {
      try {
        this.engine.resize(widthCss, heightCss);
      } catch (err) {
        console.warn('[AtlasRuntimeClient] resize failed:', err);
      }
    }
  }

  public renderFrame(): boolean {
    if (this.engine && !this.disposed) {
      try {
        return this.engine.renderFrame();
      } catch {
        return false;
      }
    }
    return false;
  }

  public dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.listeners.clear();

    if (this.engine) {
      try {
        this.engine.dispose();
      } catch {
        // Disposed safely
      }
      this.engine = null;
    }
    this.canvas = null;
  }
}
