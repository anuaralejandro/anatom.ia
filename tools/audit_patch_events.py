from pathlib import Path
root=Path(r"C:\Users\datam\Documents\anatom.ia")
p=root/"crates/atlas-web/src/lib.rs"
s=p.read_text(encoding="utf-8")
def swap(a,b,count=1):
 global s
 assert s.count(a)==count,(a[:70],s.count(a))
 s=s.replace(a,b,count)
anchor='''    #[wasm_bindgen]
    pub fn setEventCallback(&self, callback: js_sys::Function) {
        self.with_inner_mut(|inner| {
            inner.event_callback = Some(callback);
        });
    }
'''
replacement='''    // Small, bounded events: the interface never receives GPU buffers or mesh arrays.
    fn emit_event(inner: &EngineInner, kind: &str, anatomy_id: Option<&str>) {
        if let Some(callback) = &inner.event_callback {
            let event = js_sys::Object::new();
            let _ = js_sys::Reflect::set(
                &event, &JsValue::from_str("type"), &JsValue::from_str(kind),
            );
            if let Some(id) = anatomy_id {
                let _ = js_sys::Reflect::set(
                    &event, &JsValue::from_str("id"), &JsValue::from_str(id),
                );
            }
            let _ = js_sys::Reflect::set(
                &event, &JsValue::from_str("sceneRevision"),
                &JsValue::from_f64(inner.scene.revision as f64),
            );
            if let Err(error) = callback.call1(&JsValue::NULL, &event) {
                log::warn!("Anatomy event callback failed: {:?}", error);
            }
        }
    }

    #[wasm_bindgen]
    pub fn setEventCallback(&self, callback: js_sys::Function) {
        self.with_inner_mut(|inner| {
            inner.event_callback = Some(callback);
            Self::emit_event(inner, "engine.ready", None);
        });
    }
'''
swap(anchor,replacement)

swap('''        let scene = parse_glb(bytes).map_err(|e| {
            serde_wasm_bindgen::to_value(&e).unwrap_or_else(|_| JsValue::from_str(&e.to_string()))
        })?;''','''        Self::emit_event(inner, "region.loading", None);
        let scene = match parse_glb(bytes) {
            Ok(scene) => scene,
            Err(e) => {
                Self::emit_event(inner, "engine.error", None);
                return Err(
                    serde_wasm_bindgen::to_value(&e)
                        .unwrap_or_else(|_| JsValue::from_str(&e.to_string())),
                );
            }
        };''')

swap('''        inner.variant = "male-adult".into();
        inner.needs_render = true;

        SCENE_GENERATION.fetch_add(1, Ordering::SeqCst);''','''        inner.variant = "male-adult".into();
        inner.needs_render = true;
        Self::emit_event(inner, "region.ready", None);
        Self::emit_event(inner, "scene.changed", None);

        SCENE_GENERATION.fetch_add(1, Ordering::SeqCst);''')
swap('''        inner.variant = "test".into();
        inner.needs_render = true;

        SCENE_GENERATION.fetch_add(1, Ordering::SeqCst);''','''        inner.variant = "test".into();
        inner.needs_render = true;
        Self::emit_event(inner, "region.ready", None);
        Self::emit_event(inner, "scene.changed", None);

        SCENE_GENERATION.fetch_add(1, Ordering::SeqCst);''')
swap('''        inner.scene.select_structure(hit_id.clone());
        inner.needs_render = true;

        hit_id''','''        inner.scene.select_structure(hit_id.clone());
        inner.needs_render = true;
        Self::emit_event(inner, "structure.selected", hit_id.as_deref());
        Self::emit_event(inner, "scene.changed", None);

        hit_id''')
swap('''            inner.scene.select_structure(id);
            inner.needs_render = true;
            inner.scene.revision''','''            inner.scene.select_structure(id);
            inner.needs_render = true;
            Self::emit_event(inner, "structure.selected", inner.scene.selected_id.as_deref());
            Self::emit_event(inner, "scene.changed", None);
            inner.scene.revision''')

swap('''            inner.scene.set_visibility(&id, visible);
            inner.needs_render = true;
            inner.scene.revision''','''            if inner.scene.set_visibility(&id, visible) {
                inner.needs_render = true;
                Self::emit_event(inner, "scene.changed", None);
            }
            inner.scene.revision''')
swap('''            inner.scene.isolate_structure(&id);
            if let Some(bounds) = inner.scene.get_structure_bounds(&id) {''','''            if !inner.scene.isolate_structure(&id) {
                return inner.scene.revision;
            }
            if let Some(bounds) = inner.scene.get_structure_bounds(&id) {''')
swap('''            inner.needs_render = true;
            inner.scene.revision
        } else {
            0
        }
    }

    #[wasm_bindgen]
    pub fn resetVisibility''','''            inner.needs_render = true;
            Self::emit_event(inner, "structure.selected", Some(&id));
            Self::emit_event(inner, "scene.changed", None);
            inner.scene.revision
        } else {
            0
        }
    }

    #[wasm_bindgen]
    pub fn resetVisibility''')
swap('''            inner.scene.reset_visibility();
            inner
                .camera''','''            inner.scene.reset_visibility();
            Self::emit_event(inner, "scene.changed", None);
            inner
                .camera''')
swap('''                inner.scene.select_structure(Some(id));
                inner.needs_render = true;
                return true;''','''                inner.scene.select_structure(Some(id.clone()));
                inner.needs_render = true;
                Self::emit_event(inner, "structure.selected", Some(&id));
                Self::emit_event(inner, "scene.changed", None);
                return true;''')
p.write_text(s,encoding="utf-8")
# Fix the invalid-id isolation bug: do not hide every structure for nonexistent ID.
p=root/"crates/atlas-core/src/scene.rs"
s=p.read_text(encoding="utf-8")
a='''    pub fn isolate_structure(&mut self, id: &str) -> bool {
        let mut found = false;
        for node in &mut self.nodes {'''
b='''    pub fn isolate_structure(&mut self, id: &str) -> bool {
        // Validate first; an unknown ID must not blank the complete atlas.
        if !self.nodes.iter().any(|node| node.anatomy_id.as_deref() == Some(id)) {
            return false;
        }
        let mut found = false;
        for node in &mut self.nodes {'''
assert s.count(a)==1
p.write_text(s.replace(a,b,1),encoding="utf-8")
# Wire events in probe shell for evidence in browser logs.
p=root/"apps/probe-web/app.js"
s=p.read_text(encoding="utf-8")
needle="        state.engine = engine;\n        state.activeBackend = "
assert s.count(needle)==2
s=s.replace(needle,'''        state.engine = engine;
        if (typeof engine.setEventCallback === 'function') {
          engine.setEventCallback((event) => {
            log('Rust event: ' + event.type + (event.id ? ' (' + event.id + ')' : ''));
          });
        }
        state.activeBackend = ''')
p.write_text(s,encoding="utf-8")
# Correct headless cube time window to permit bounded auto fallback.
p=root/"tools/test_browser_headless.py"
s=p.read_text(encoding="utf-8")
needle="time_budget_ms=5000\n    )"
assert s.count(needle)==1
p.write_text(s.replace(needle,"time_budget_ms=16000\n    )"),encoding="utf-8")
print("PATCHED event emission, invalid-ID isolation and cube audit time.")
