use std::cell::RefCell;
use std::rc::Rc;
use std::sync::atomic::{AtomicU32, Ordering};

use atlas_core::camera::Camera;
use atlas_core::glb::parse_glb;
use atlas_core::picking::pick_scene;
use atlas_core::renderer::Renderer;
use atlas_core::scene::Scene;
#[allow(unused_imports)]
use atlas_core::types::{
    BackendPreference, BootstrapOptions, EngineCapabilities, EngineError, ErrorCode, RenderStats,
    SceneSnapshot, StructureMetadata,
};
use wasm_bindgen::prelude::*;
#[allow(unused_imports)]
use web_sys::{HtmlCanvasElement, Window};

static SCENE_GENERATION: AtomicU32 = AtomicU32::new(1);

struct EngineInner {
    canvas: HtmlCanvasElement,
    surface: wgpu::Surface<'static>,
    renderer: Renderer,
    scene: Scene,
    camera: Camera,
    dpr: f32,
    needs_render: bool,
    region: String,
    variant: String,
    event_callback: Option<js_sys::Function>,
}

#[wasm_bindgen]
pub struct AtlasEngine {
    inner: Rc<RefCell<Option<EngineInner>>>,
}

#[wasm_bindgen]
#[allow(non_snake_case)]
impl AtlasEngine {
    #[wasm_bindgen(constructor)]
    pub fn new() -> Self {
        #[cfg(target_arch = "wasm32")]
        console_error_panic_hook::set_once();
        let _ = console_log::init_with_level(log::Level::Info);

        Self {
            inner: Rc::new(RefCell::new(None)),
        }
    }

    #[allow(clippy::collapsible_if)]
    fn with_inner_mut<F: FnOnce(&mut EngineInner)>(&self, f: F) {
        if let Ok(mut borrow) = self.inner.try_borrow_mut() {
            if let Some(inner) = borrow.as_mut() {
                f(inner);
            }
        }
    }

    // Small, bounded events: the interface never receives GPU buffers or mesh arrays.
    fn emit_event(inner: &EngineInner, kind: &str, anatomy_id: Option<&str>) {
        if let Some(callback) = &inner.event_callback {
            let event = js_sys::Object::new();
            let _ =
                js_sys::Reflect::set(&event, &JsValue::from_str("type"), &JsValue::from_str(kind));
            if let Some(id) = anatomy_id {
                let _ =
                    js_sys::Reflect::set(&event, &JsValue::from_str("id"), &JsValue::from_str(id));
            }
            let _ = js_sys::Reflect::set(
                &event,
                &JsValue::from_str("sceneRevision"),
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

    #[wasm_bindgen]
    pub fn initialize(&self, canvas: HtmlCanvasElement, options_val: JsValue) -> js_sys::Promise {
        let inner_rc = self.inner.clone();
        let options: BootstrapOptions =
            serde_wasm_bindgen::from_value(options_val).unwrap_or_default();

        wasm_bindgen_futures::future_to_promise(async move {
            let res = Self::init_async(canvas, options).await;
            match res {
                Ok(engine_inner) => {
                    let caps = engine_inner.renderer.capabilities.clone();
                    let caps_val = serde_wasm_bindgen::to_value(&caps)
                        .map_err(|e| JsValue::from_str(&e.to_string()))?;

                    *inner_rc.borrow_mut() = Some(engine_inner);
                    Ok(caps_val)
                }
                Err(err) => {
                    let err_val = serde_wasm_bindgen::to_value(&err)
                        .unwrap_or_else(|_| JsValue::from_str(&err.to_string()));
                    Err(err_val)
                }
            }
        })
    }

    async fn init_async(
        canvas: HtmlCanvasElement,
        options: BootstrapOptions,
    ) -> Result<EngineInner, EngineError> {
        #[cfg(not(target_arch = "wasm32"))]
        {
            let _ = (canvas, options);
            Err(EngineError::new(
                ErrorCode::GpuUnavailable,
                "atlas-web canvas initialization requires wasm32 target",
                false,
            ))
        }

        #[cfg(target_arch = "wasm32")]
        {
            let window: Window = web_sys::window().ok_or_else(|| {
                EngineError::new(
                    ErrorCode::GpuUnavailable,
                    "No global window object found",
                    false,
                )
            })?;

            let dpr = options
                .dpr
                .unwrap_or_else(|| window.device_pixel_ratio() as f32);
            let client_width = canvas.client_width().max(1) as u32;
            let client_height = canvas.client_height().max(1) as u32;

            let width = ((client_width as f32) * dpr).round() as u32;
            let height = ((client_height as f32) * dpr).round() as u32;

            canvas.set_width(width);
            canvas.set_height(height);

            let requested = options.preferred_backend;
            log::info!(
                "AtlasEngine initializing: requested backend = {:?}",
                requested
            );

            let mut instance_desc = wgpu::InstanceDescriptor::new_without_display_handle();
            instance_desc.backends = match requested {
                BackendPreference::WebGpu => wgpu::Backends::BROWSER_WEBGPU,
                BackendPreference::WebGl2 => wgpu::Backends::GL,
                BackendPreference::Auto => wgpu::Backends::all(),
            };

            let instance = wgpu::Instance::new(instance_desc);

            let surface = instance
                .create_surface(wgpu::SurfaceTarget::Canvas(canvas.clone()))
                .map_err(|e| {
                    EngineError::new(
                        ErrorCode::GpuUnavailable,
                        format!("Failed to create surface from canvas: {}", e),
                        false,
                    )
                })?;

            let adapter = instance
                .request_adapter(&wgpu::RequestAdapterOptions {
                    power_preference: match options.power_preference.as_deref() {
                        Some("high-performance") => wgpu::PowerPreference::HighPerformance,
                        _ => wgpu::PowerPreference::LowPower,
                    },
                    compatible_surface: Some(&surface),
                    force_fallback_adapter: false,
                    apply_limit_buckets: false,
                })
                .await
                .map_err(|e| {
                    EngineError::new(
                        ErrorCode::GpuUnavailable,
                        format!("Failed to obtain GPU adapter: {}", e),
                        false,
                    )
                })?;

            let adapter_info = adapter.get_info();
            log::info!(
                "Adapter found: name='{}', backend={:?}, device_type={:?}",
                adapter_info.name,
                adapter_info.backend,
                adapter_info.device_type
            );

            let is_webgl = adapter_info.backend == wgpu::Backend::Gl;
            let required_limits = if is_webgl {
                wgpu::Limits::downlevel_webgl2_defaults()
            } else {
                wgpu::Limits::default()
            };

            let (device, queue) = adapter
                .request_device(&wgpu::DeviceDescriptor {
                    label: Some("atlas_device"),
                    required_features: wgpu::Features::empty(),
                    required_limits,
                    memory_hints: Default::default(),
                    experimental_features: Default::default(),
                    trace: wgpu::Trace::Off,
                })
                .await
                .map_err(|e| {
                    EngineError::new(
                        ErrorCode::GpuUnavailable,
                        format!("Failed to create GPU device: {}", e),
                        false,
                    )
                })?;

            let surface_caps = surface.get_capabilities(&adapter);
            let surface_format = surface_caps
                .formats
                .iter()
                .copied()
                .find(|f| f.is_srgb())
                .unwrap_or_else(|| {
                    surface_caps
                        .formats
                        .first()
                        .copied()
                        .unwrap_or(wgpu::TextureFormat::Rgba8Unorm)
                });

            let surface_config = wgpu::SurfaceConfiguration {
                usage: wgpu::TextureUsages::RENDER_ATTACHMENT,
                format: surface_format,
                color_space: wgpu::SurfaceColorSpace::Auto,
                width,
                height,
                present_mode: wgpu::PresentMode::AutoVsync,
                alpha_mode: surface_caps.alpha_modes[0],
                view_formats: vec![],
                desired_maximum_frame_latency: 2,
            };
            surface.configure(&device, &surface_config);

            let backend_str = match adapter_info.backend {
                wgpu::Backend::BrowserWebGpu => "webgpu".to_string(),
                wgpu::Backend::Gl => "webgl2".to_string(),
                other => format!("{:?}", other).to_lowercase(),
            };

            let capabilities = EngineCapabilities {
                backend: backend_str,
                adapter_name: adapter_info.name,
                backend_type: format!("{:?}", adapter_info.backend),
                max_texture_dimension_2d: adapter.limits().max_texture_dimension_2d,
                supports_depth24_plus: true,
            };

            let mut renderer =
                Renderer::new(device, queue, surface_format, width, height, capabilities);

            let scene = renderer.create_synthetic_cube_scene();

            let mut camera = Camera::default();
            camera.aspect = (width as f32) / (height as f32).max(1.0);
            camera.fit_bounds(scene.bounds.min, scene.bounds.max);

            Ok(EngineInner {
                canvas,
                surface,
                renderer,
                scene,
                camera,
                dpr,
                needs_render: true,
                region: "synthetic-cube".to_string(),
                variant: "test".to_string(),
                event_callback: None,
            })
        }
    }

    #[wasm_bindgen]
    pub fn loadGlbBytes(&self, bytes: &[u8]) -> Result<JsValue, JsValue> {
        let mut borrow = self.inner.borrow_mut();
        let inner = borrow
            .as_mut()
            .ok_or_else(|| JsValue::from_str("Engine not initialized"))?;

        Self::emit_event(inner, "region.loading", None);
        let scene = match parse_glb(bytes) {
            Ok(scene) => scene,
            Err(e) => {
                Self::emit_event(inner, "engine.error", None);
                return Err(serde_wasm_bindgen::to_value(&e)
                    .unwrap_or_else(|_| JsValue::from_str(&e.to_string())));
            }
        };

        inner.renderer.upload_scene(&scene);
        inner.camera.fit_bounds(scene.bounds.min, scene.bounds.max);
        inner.scene = scene;
        inner.region = "pelvis".into();
        inner.variant = "male-adult".into();
        inner.needs_render = true;
        Self::emit_event(inner, "region.ready", None);
        Self::emit_event(inner, "scene.changed", None);

        SCENE_GENERATION.fetch_add(1, Ordering::SeqCst);

        let snapshot = self.snapshot_internal(inner);
        serde_wasm_bindgen::to_value(&snapshot).map_err(|e| JsValue::from_str(&e.to_string()))
    }

    #[wasm_bindgen]
    pub fn loadSyntheticCube(&self) -> Result<JsValue, JsValue> {
        let mut borrow = self.inner.borrow_mut();
        let inner = borrow
            .as_mut()
            .ok_or_else(|| JsValue::from_str("Engine not initialized"))?;

        let scene = inner.renderer.create_synthetic_cube_scene();
        inner.camera.fit_bounds(scene.bounds.min, scene.bounds.max);
        inner.scene = scene;
        inner.region = "synthetic-cube".into();
        inner.variant = "test".into();
        inner.needs_render = true;
        Self::emit_event(inner, "region.ready", None);
        Self::emit_event(inner, "scene.changed", None);

        SCENE_GENERATION.fetch_add(1, Ordering::SeqCst);
        let snapshot = self.snapshot_internal(inner);
        serde_wasm_bindgen::to_value(&snapshot).map_err(|e| JsValue::from_str(&e.to_string()))
    }

    #[wasm_bindgen]
    pub fn selectAt(&self, x_css: f32, y_css: f32) -> Option<String> {
        let mut borrow = self.inner.borrow_mut();
        let inner = borrow.as_mut()?;

        let client_w = inner.canvas.client_width() as f32;
        let client_h = inner.canvas.client_height() as f32;

        let ray = inner
            .camera
            .ray_from_screen(x_css, y_css, client_w, client_h);
        let hit = pick_scene(&inner.scene, &ray);

        let hit_id = hit.map(|h| h.anatomy_id);
        inner.scene.select_structure(hit_id.clone());
        inner.needs_render = true;
        Self::emit_event(inner, "structure.selected", hit_id.as_deref());
        Self::emit_event(inner, "scene.changed", None);

        hit_id
    }

    #[wasm_bindgen]
    pub fn selectStructure(&self, id: Option<String>) -> u32 {
        let mut borrow = self.inner.borrow_mut();
        if let Some(inner) = borrow.as_mut() {
            inner.scene.select_structure(id);
            inner.needs_render = true;
            Self::emit_event(
                inner,
                "structure.selected",
                inner.scene.selected_id.as_deref(),
            );
            Self::emit_event(inner, "scene.changed", None);
            inner.scene.revision
        } else {
            0
        }
    }

    #[wasm_bindgen]
    pub fn setVisibility(&self, id: String, visible: bool) -> u32 {
        let mut borrow = self.inner.borrow_mut();
        if let Some(inner) = borrow.as_mut() {
            if inner.scene.set_visibility(&id, visible) {
                inner.needs_render = true;
                Self::emit_event(inner, "scene.changed", None);
            }
            inner.scene.revision
        } else {
            0
        }
    }

    #[wasm_bindgen]
    pub fn isolateStructure(&self, id: String) -> u32 {
        let mut borrow = self.inner.borrow_mut();
        if let Some(inner) = borrow.as_mut() {
            if !inner.scene.isolate_structure(&id) {
                return inner.scene.revision;
            }
            if let Some(bounds) = inner.scene.get_structure_bounds(&id) {
                inner.camera.fit_bounds(bounds.min, bounds.max);
            }
            inner.needs_render = true;
            Self::emit_event(inner, "structure.selected", Some(&id));
            Self::emit_event(inner, "scene.changed", None);
            inner.scene.revision
        } else {
            0
        }
    }

    #[wasm_bindgen]
    pub fn resetVisibility(&self) -> u32 {
        let mut borrow = self.inner.borrow_mut();
        if let Some(inner) = borrow.as_mut() {
            inner.scene.reset_visibility();
            Self::emit_event(inner, "scene.changed", None);
            inner
                .camera
                .fit_bounds(inner.scene.bounds.min, inner.scene.bounds.max);
            inner.needs_render = true;
            inner.scene.revision
        } else {
            0
        }
    }

    #[wasm_bindgen]
    pub fn focusStructure(&self, id: String) -> bool {
        let mut borrow = self.inner.borrow_mut();
        if let Some(inner) = borrow.as_mut() {
            let bounds = inner.scene.get_structure_bounds(&id);
            if let Some(b) = bounds {
                inner.camera.fit_bounds(b.min, b.max);
                inner.scene.select_structure(Some(id.clone()));
                inner.needs_render = true;
                Self::emit_event(inner, "structure.selected", Some(&id));
                Self::emit_event(inner, "scene.changed", None);
                return true;
            }
        }
        false
    }

    #[wasm_bindgen]
    pub fn resetCamera(&self) -> u32 {
        let mut borrow = self.inner.borrow_mut();
        if let Some(inner) = borrow.as_mut() {
            inner.camera = Camera::default();
            inner.camera.aspect =
                (inner.renderer.width as f32) / (inner.renderer.height as f32).max(1.0);
            inner
                .camera
                .fit_bounds(inner.scene.bounds.min, inner.scene.bounds.max);
            inner.needs_render = true;
            inner.scene.revision
        } else {
            0
        }
    }

    #[wasm_bindgen]
    pub fn setCameraPreset(&self, preset_id: u32) {
        self.with_inner_mut(|inner| {
            inner.camera.set_preset(preset_id);
            inner.needs_render = true;
        });
    }

    #[wasm_bindgen]
    pub fn orbit(&self, delta_x: f32, delta_y: f32) {
        self.with_inner_mut(|inner| {
            inner.camera.orbit(delta_x, delta_y);
            inner.needs_render = true;
        });
    }

    #[wasm_bindgen]
    pub fn pan(&self, delta_x: f32, delta_y: f32) {
        self.with_inner_mut(|inner| {
            inner.camera.pan(delta_x, delta_y);
            inner.needs_render = true;
        });
    }

    #[wasm_bindgen]
    pub fn zoom(&self, delta: f32) {
        self.with_inner_mut(|inner| {
            inner.camera.zoom(delta);
            inner.needs_render = true;
        });
    }

    #[wasm_bindgen]
    pub fn resize(&self, width_css: u32, height_css: u32) {
        self.with_inner_mut(|inner| {
            let physical_w = ((width_css as f32) * inner.dpr).round() as u32;
            let physical_h = ((height_css as f32) * inner.dpr).round() as u32;

            inner.canvas.set_width(physical_w);
            inner.canvas.set_height(physical_h);

            let surface_config = wgpu::SurfaceConfiguration {
                usage: wgpu::TextureUsages::RENDER_ATTACHMENT,
                format: inner.renderer.surface_format,
                color_space: wgpu::SurfaceColorSpace::Auto,
                width: physical_w,
                height: physical_h,
                present_mode: wgpu::PresentMode::AutoVsync,
                alpha_mode: wgpu::CompositeAlphaMode::Auto,
                view_formats: vec![],
                desired_maximum_frame_latency: 2,
            };
            inner
                .surface
                .configure(&inner.renderer.device, &surface_config);
            inner.renderer.resize(physical_w, physical_h);
            inner.camera.aspect = (physical_w as f32) / (physical_h as f32).max(1.0);
            inner.needs_render = true;
        });
    }

    #[wasm_bindgen]
    pub fn setTheme(&self, dark: bool) {
        self.with_inner_mut(|inner| {
            if dark {
                inner.renderer.set_clear_color(0.09, 0.10, 0.13);
            } else {
                inner.renderer.set_clear_color(0.92, 0.93, 0.95);
            }
            inner.needs_render = true;
        });
    }

    #[wasm_bindgen]
    pub fn renderFrame(&self) -> bool {
        let mut borrow = match self.inner.try_borrow_mut() {
            Ok(b) => b,
            Err(_) => return false,
        };
        let inner = match borrow.as_mut() {
            Some(i) => i,
            None => return false,
        };

        if !inner.needs_render {
            return false;
        }

        let output = match inner.surface.get_current_texture() {
            wgpu::CurrentSurfaceTexture::Success(tex)
            | wgpu::CurrentSurfaceTexture::Suboptimal(tex) => tex,
            wgpu::CurrentSurfaceTexture::Lost | wgpu::CurrentSurfaceTexture::Outdated => {
                log::warn!("Surface lost or outdated, reconfiguring...");
                inner
                    .renderer
                    .resize(inner.renderer.width, inner.renderer.height);
                return false;
            }
            wgpu::CurrentSurfaceTexture::Occluded => {
                // Window minimized/occluded, skip frame
                return false;
            }
            other => {
                log::warn!("Surface texture acquisition status: {:?}", other);
                return false;
            }
        };

        let view = output
            .texture
            .create_view(&wgpu::TextureViewDescriptor::default());

        let res = inner.renderer.render(&view, &inner.camera, &inner.scene);
        inner.renderer.queue.present(output);

        inner.needs_render = false;
        res.is_ok()
    }

    #[wasm_bindgen]
    pub fn requestRender(&self) {
        self.with_inner_mut(|inner| {
            inner.needs_render = true;
        });
    }

    #[wasm_bindgen]
    pub fn getSceneSnapshot(&self) -> JsValue {
        let borrow = self.inner.borrow();
        if let Some(inner) = borrow.as_ref() {
            let snap = self.snapshot_internal(inner);
            serde_wasm_bindgen::to_value(&snap).unwrap_or(JsValue::NULL)
        } else {
            JsValue::NULL
        }
    }

    #[wasm_bindgen]
    pub fn getCapabilities(&self) -> JsValue {
        let borrow = self.inner.borrow();
        if let Some(inner) = borrow.as_ref() {
            serde_wasm_bindgen::to_value(&inner.renderer.capabilities).unwrap_or(JsValue::NULL)
        } else {
            JsValue::NULL
        }
    }

    #[wasm_bindgen]
    pub fn getStats(&self) -> JsValue {
        let borrow = self.inner.borrow();
        if let Some(inner) = borrow.as_ref() {
            let mut total_tris = 0;
            let mut total_prims = 0;
            let mut visible_nodes = 0;
            for node in &inner.scene.nodes {
                if node.visible {
                    visible_nodes += 1;
                    if let Some(mesh) = node.mesh_index.and_then(|idx| inner.scene.meshes.get(idx))
                    {
                        total_prims += mesh.primitives.len();
                        for p in &mesh.primitives {
                            total_tris += p.indices.len() / 3;
                        }
                    }
                }
            }
            let stats = RenderStats {
                total_nodes: inner.scene.nodes.len(),
                visible_nodes,
                primitive_count: total_prims,
                triangle_count: total_tris,
                draw_call_count: total_prims,
                backend: inner.renderer.capabilities.backend.clone(),
            };
            serde_wasm_bindgen::to_value(&stats).unwrap_or(JsValue::NULL)
        } else {
            JsValue::NULL
        }
    }

    #[wasm_bindgen]
    pub fn getStructures(&self) -> JsValue {
        let borrow = self.inner.borrow();
        if let Some(inner) = borrow.as_ref() {
            let mut list = Vec::new();
            for node in &inner.scene.nodes {
                if let Some(ref aid) = node.anatomy_id {
                    let mut prim_count = 0;
                    let mut tri_count = 0;
                    if let Some(mesh) = node.mesh_index.and_then(|idx| inner.scene.meshes.get(idx))
                    {
                        prim_count = mesh.primitives.len();
                        for p in &mesh.primitives {
                            tri_count += p.indices.len() / 3;
                        }
                    }

                    list.push(StructureMetadata {
                        id: aid.clone(),
                        name_es: node.name.clone().unwrap_or_else(|| aid.clone()),
                        name_en: node.name.clone().unwrap_or_else(|| aid.clone()),
                        side: if aid.contains(":left") {
                            "left".into()
                        } else if aid.contains(":right") {
                            "right".into()
                        } else {
                            "unpaired".into()
                        },
                        primitive_count: prim_count,
                        triangle_count: tri_count,
                        visible: node.visible,
                    });
                }
            }
            serde_wasm_bindgen::to_value(&list).unwrap_or(JsValue::NULL)
        } else {
            JsValue::NULL
        }
    }

    #[wasm_bindgen]
    pub fn dispose(&self) {
        let mut borrow = self.inner.borrow_mut();
        *borrow = None;
    }

    fn snapshot_internal(&self, inner: &EngineInner) -> SceneSnapshot {
        SceneSnapshot {
            region: inner.region.clone(),
            variant: inner.variant.clone(),
            selected_id: inner.scene.selected_id.clone(),
            scene_revision: inner.scene.revision,
            visible_ids: inner.scene.get_visible_ids(),
            quality: "medium".into(),
            backend: inner.renderer.capabilities.backend.clone(),
        }
    }
}

impl Default for AtlasEngine {
    fn default() -> Self {
        Self::new()
    }
}
