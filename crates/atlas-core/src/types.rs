use serde::{Deserialize, Serialize};

pub type AnatomyId = String;
pub type RegionId = String;
pub type VariantId = String;
pub type RequestId = u32;
pub type SceneGeneration = u32;
pub type SceneRevision = u32;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "lowercase")]
pub enum BackendPreference {
    #[default]
    Auto,
    WebGpu,
    WebGl2,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BootstrapOptions {
    #[serde(default)]
    pub preferred_backend: BackendPreference,
    pub power_preference: Option<String>,
    pub dpr: Option<f32>,
}

impl Default for BootstrapOptions {
    fn default() -> Self {
        Self {
            preferred_backend: BackendPreference::Auto,
            power_preference: None,
            dpr: None,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EngineCapabilities {
    pub backend: String,
    pub adapter_name: String,
    pub backend_type: String,
    pub max_texture_dimension_2d: u32,
    pub supports_depth24_plus: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ErrorCode {
    #[serde(rename = "GPU_UNAVAILABLE")]
    GpuUnavailable,
    #[serde(rename = "GPU_DEVICE_LOST")]
    GpuDeviceLost,
    #[serde(rename = "SHADER_UNSUPPORTED")]
    ShaderUnsupported,
    #[serde(rename = "ASSET_NOT_FOUND")]
    AssetNotFound,
    #[serde(rename = "ASSET_CORRUPT")]
    AssetCorrupt,
    #[serde(rename = "ASSET_UNSUPPORTED_EXTENSION")]
    AssetUnsupportedExtension,
    #[serde(rename = "REGION_UNAVAILABLE")]
    RegionUnavailable,
    #[serde(rename = "STRUCTURE_NOT_FOUND")]
    StructureNotFound,
    #[serde(rename = "NETWORK_ERROR")]
    NetworkError,
    #[serde(rename = "MEMORY_LIMIT")]
    MemoryLimit,
    #[serde(rename = "INVALID_COORDINATES")]
    InvalidCoordinates,
    #[serde(rename = "CANCELLED")]
    Cancelled,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EngineError {
    pub code: ErrorCode,
    pub recoverable: bool,
    pub detail: Option<String>,
    pub request_id: Option<RequestId>,
    pub scene_generation: Option<SceneGeneration>,
}

impl EngineError {
    pub fn new(code: ErrorCode, detail: impl Into<String>, recoverable: bool) -> Self {
        Self {
            code,
            recoverable,
            detail: Some(detail.into()),
            request_id: None,
            scene_generation: None,
        }
    }
}

impl std::fmt::Display for EngineError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "{:?}: {}",
            self.code,
            self.detail.as_deref().unwrap_or("unknown error")
        )
    }
}

impl std::error::Error for EngineError {}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SceneSnapshot {
    pub region: String,
    pub variant: String,
    pub selected_id: Option<AnatomyId>,
    pub scene_revision: SceneRevision,
    pub visible_ids: Vec<AnatomyId>,
    pub quality: String,
    pub backend: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StructureMetadata {
    pub id: AnatomyId,
    pub name_es: String,
    pub name_en: String,
    pub side: String,
    pub primitive_count: usize,
    pub triangle_count: usize,
    pub visible: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RenderStats {
    pub total_nodes: usize,
    pub visible_nodes: usize,
    pub primitive_count: usize,
    pub triangle_count: usize,
    pub draw_call_count: usize,
    pub backend: String,
}
