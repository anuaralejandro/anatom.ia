import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { AtlasRuntimeClient } from '../src/runtime/AtlasRuntimeClient';
import type { AtlasEngineLike } from '../src/runtime/AtlasRuntimeClient';

describe('AtlasRuntimeClient Lifecycle & Architecture', () => {
  it('manages request IDs and generations monotonically', () => {
    const client = new AtlasRuntimeClient();
    const req1 = client.nextRequestId();
    const req2 = client.nextRequestId();
    assert.equal(req2, req1 + 1);

    const gen1 = client.nextGeneration();
    const gen2 = client.nextGeneration();
    assert.equal(gen2, gen1 + 1);
    client.dispose();
  });

  it('decouples event callbacks via microtask queue to avoid Rust RefCell reentrancy', async () => {
    let capturedCallback: ((ev: unknown) => void) | null = null;

    const mockEngine: AtlasEngineLike = {
      initialize: async () => {},
      renderFrame: () => true,
      requestRender: () => {},
      resize: () => {},
      orbit: () => {},
      pan: () => {},
      zoom: () => {},
      resetCamera: () => 0,
      setCameraPreset: () => {},
      selectStructure: () => 0,
      selectAt: () => undefined,
      isolateStructure: () => 0,
      setVisibility: () => 0,
      resetVisibility: () => 0,
      setQualityProfile: () => {},
      setTheme: () => {},
      getSceneSnapshot: () => ({ selected_id: 'ta2:1071', scene_revision: 1, visible_ids: ['ta2:1071'] }),
      getCapabilities: () => ({ adapter_name: 'Mock' }),
      getMemoryStats: () => ({ budget_bytes: 100 }),
      setEventCallback: (cb) => {
        capturedCallback = cb;
      },
      dispose: () => {},
    };

    const client = new AtlasRuntimeClient(mockEngine);
    assert.ok(capturedCallback, 'setEventCallback must be registered on engine');

    const receivedEvents: string[] = [];
    client.addEventListener((e) => {
      receivedEvents.push(e.type);
    });

    // Simulate Rust calling back synchronously during borrow
    (capturedCallback as (ev: unknown) => void)({ type: 'region.ready', requestId: 1 });

    // In the synchronous turn, event is queued in microtask, not delivered immediately
    assert.equal(receivedEvents.length, 0, 'Event must not fire synchronously in same callstack');

    // Await microtask
    await Promise.resolve();
    assert.equal(receivedEvents.length, 1);
    assert.equal(receivedEvents[0], 'region.ready');

    client.dispose();
  });

  it('disposes idempotently and clears all event subscriptions', () => {
    let disposedCount = 0;
    const mockEngine: AtlasEngineLike = {
      initialize: async () => {},
      renderFrame: () => true,
      requestRender: () => {},
      resize: () => {},
      orbit: () => {},
      pan: () => {},
      zoom: () => {},
      resetCamera: () => 0,
      setCameraPreset: () => {},
      selectStructure: () => 0,
      selectAt: () => undefined,
      isolateStructure: () => 0,
      setVisibility: () => 0,
      resetVisibility: () => 0,
      setQualityProfile: () => {},
      setTheme: () => {},
      getSceneSnapshot: () => ({}),
      getCapabilities: () => ({}),
      getMemoryStats: () => ({}),
      setEventCallback: () => {},
      dispose: () => {
        disposedCount++;
      },
    };

    const client = new AtlasRuntimeClient(mockEngine);
    client.dispose();
    client.dispose(); // second call must be a no-op
    assert.equal(disposedCount, 1, 'Engine dispose must only be invoked once');
  });
});
