import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { uiStore, uiActions } from '../src/store/useUIStore';

describe('UI Store & Anatomy Selection State', () => {
  it('initializes with Obsidian Navy dark theme and Sacrum selected by default', () => {
    const state = uiStore.getState();
    assert.equal(state.theme, 'dark');
    assert.equal(state.selectedId, 'ta2:1071');
    assert.equal(state.structures.length, 26);
  });

  it('toggles structure visibility without mutating other structures', () => {
    uiActions.toggleVisibility('ta2:1071');
    const s1 = uiStore.getState().structures.find((s) => s.id === 'ta2:1071');
    assert.equal(s1?.visible, false);

    uiActions.toggleVisibility('ta2:1071');
    const s2 = uiStore.getState().structures.find((s) => s.id === 'ta2:1071');
    assert.equal(s2?.visible, true);
  });

  it('isolates target structure and hides all others', () => {
    uiActions.isolateStructure('ta2:1092'); // Coccyx
    const state = uiStore.getState();
    assert.equal(state.selectedId, 'ta2:1092');

    const visibleStructures = state.structures.filter((s) => s.visible);
    assert.equal(visibleStructures.length, 1);
    assert.equal(visibleStructures[0].id, 'ta2:1092');

    // Reset visibility brings all 26 back
    uiActions.resetVisibility();
    const allVisible = uiStore.getState().structures.filter((s) => s.visible);
    assert.equal(allVisible.length, 26);
  });

  it('manages mutually exclusive overlays (no simultaneous overlays)', () => {
    uiActions.openOverlay('explorer');
    assert.equal(uiStore.getState().activeOverlay, 'explorer');

    // Opening inspector replaces explorer
    uiActions.openOverlay('inspector');
    assert.equal(uiStore.getState().activeOverlay, 'inspector');

    uiActions.closeOverlay();
    assert.equal(uiStore.getState().activeOverlay, 'none');
  });

  it('manages sheet snap points cleanly', () => {
    uiActions.setSheetSnap('mid');
    assert.equal(uiStore.getState().sheetSnap, 'mid');

    uiActions.setSheetSnap('expanded');
    assert.equal(uiStore.getState().sheetSnap, 'expanded');

    uiActions.setSheetSnap('collapsed');
    assert.equal(uiStore.getState().sheetSnap, 'collapsed');
  });
});
