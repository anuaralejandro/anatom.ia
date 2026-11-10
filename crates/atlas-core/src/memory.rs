use serde::{Deserialize, Serialize};

use crate::scene::Scene;
use crate::types::{EngineError, ErrorCode, RequestId, SceneGeneration, SceneRevision};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "lowercase")]
pub enum QualityProfile {
    Low,
    #[default]
    Medium,
    High,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct MemoryBudget {
    pub gpu_resident_budget_bytes: usize,
    pub cpu_decoded_budget_bytes: usize,
    pub concurrent_fetches: usize,
}

impl QualityProfile {
    pub fn budget(&self) -> MemoryBudget {
        match self {
            QualityProfile::Low => MemoryBudget {
                gpu_resident_budget_bytes: 64 * 1024 * 1024,
                cpu_decoded_budget_bytes: 48 * 1024 * 1024,
                concurrent_fetches: 2,
            },
            QualityProfile::Medium => MemoryBudget {
                gpu_resident_budget_bytes: 128 * 1024 * 1024,
                cpu_decoded_budget_bytes: 96 * 1024 * 1024,
                concurrent_fetches: 3,
            },
            QualityProfile::High => MemoryBudget {
                gpu_resident_budget_bytes: 256 * 1024 * 1024,
                cpu_decoded_budget_bytes: 160 * 1024 * 1024,
                concurrent_fetches: 4,
            },
        }
    }
}

/// Explicit memory accounting separating distinct allocation categories.
/// Note: All GPU numbers represent runtime-calculated buffer allocations,
/// NOT driver-level physical VRAM.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct MemoryStats {
    // Legacy fields for backwards compatibility with JS probe & tests
    pub resident_gpu_bytes: usize,
    pub decoded_cpu_bytes: usize,
    pub cached_storage_bytes: usize,
    pub evictions_count: u32,
    pub current_generation: SceneGeneration,
    pub active_request_id: Option<RequestId>,
    pub scene_revision: SceneRevision,
    pub quality_profile: QualityProfile,
    pub gpu_budget_bytes: usize,
    pub cpu_budget_bytes: usize,

    // M04-H2 Explicit Estimation Breakdown (NOT physical VRAM)
    pub gpu_buffer_allocated_estimate: usize,
    pub gpu_depth_render_target_estimate: usize,
    pub resident_gpu_bytes_estimate: usize,
    pub cpu_scene_decoded_estimate: usize,
    pub cpu_staging_bytes_estimate: usize,
    pub verified_blob_bytes: usize,
    pub cache_storage_estimate: usize,
    pub peak_overlap_bytes_estimate: usize,
    pub memory_budget_gpu_bytes: usize,
    pub memory_budget_cpu_bytes: usize,
    pub is_within_budget: bool,
}

#[derive(Debug, Clone)]
pub struct MemoryTracker {
    profile: QualityProfile,
    custom_budget: Option<MemoryBudget>,
    gpu_buffer_allocated: usize,
    gpu_depth_estimate: usize,
    cpu_decoded_bytes: usize,
    cpu_staging_bytes: usize,
    verified_blob_bytes: usize,
    cached_storage_bytes: usize,
    peak_overlap_bytes: usize,
    evictions_count: u32,
    generation: SceneGeneration,
    active_request_id: Option<RequestId>,
}

impl Default for MemoryTracker {
    fn default() -> Self {
        Self::new(QualityProfile::Medium)
    }
}

impl MemoryTracker {
    pub fn new(profile: QualityProfile) -> Self {
        Self {
            profile,
            custom_budget: None,
            gpu_buffer_allocated: 0,
            gpu_depth_estimate: 0,
            cpu_decoded_bytes: 0,
            cpu_staging_bytes: 0,
            verified_blob_bytes: 0,
            cached_storage_bytes: 0,
            peak_overlap_bytes: 0,
            evictions_count: 0,
            generation: 1,
            active_request_id: None,
        }
    }

    pub fn set_profile(&mut self, profile: QualityProfile) {
        self.profile = profile;
        self.custom_budget = None;
    }

    pub fn set_custom_budget(&mut self, budget: Option<MemoryBudget>) {
        self.custom_budget = budget;
    }

    pub fn budget(&self) -> MemoryBudget {
        self.custom_budget.unwrap_or_else(|| self.profile.budget())
    }

    pub fn profile(&self) -> QualityProfile {
        self.profile
    }

    pub fn set_gpu_buffer_allocated(&mut self, bytes: usize) {
        self.gpu_buffer_allocated = bytes;
    }

    pub fn set_gpu_depth_estimate(&mut self, bytes: usize) {
        self.gpu_depth_estimate = bytes;
    }

    pub fn set_resident_gpu_bytes(&mut self, bytes: usize) {
        self.gpu_buffer_allocated = bytes;
    }

    pub fn set_decoded_cpu_bytes(&mut self, bytes: usize) {
        self.cpu_decoded_bytes = bytes;
    }

    pub fn set_cpu_staging_bytes(&mut self, bytes: usize) {
        self.cpu_staging_bytes = bytes;
    }

    pub fn set_verified_blob_bytes(&mut self, bytes: usize) {
        self.verified_blob_bytes = bytes;
    }

    pub fn set_cached_storage_bytes(&mut self, bytes: usize) {
        self.cached_storage_bytes = bytes;
    }

    pub fn set_peak_overlap_bytes(&mut self, bytes: usize) {
        self.peak_overlap_bytes = bytes;
    }

    pub fn record_eviction(&mut self) {
        self.evictions_count += 1;
    }

    pub fn next_generation(&mut self, request_id: Option<RequestId>) -> SceneGeneration {
        self.generation = self.generation.wrapping_add(1);
        if self.generation == 0 {
            self.generation = 1;
        }
        self.active_request_id = request_id;
        self.generation
    }

    pub fn current_generation(&self) -> SceneGeneration {
        self.generation
    }

    pub fn is_within_budget(&self) -> bool {
        let budget = self.budget();
        let total_gpu = self.gpu_buffer_allocated + self.gpu_depth_estimate;
        total_gpu <= budget.gpu_resident_budget_bytes
            && self.cpu_decoded_bytes <= budget.cpu_decoded_budget_bytes
    }

    /// Preflight check for candidate swap allocation.
    /// Rejects before allocating resources if peak swap usage exceeds budget.
    pub fn preflight_swap_budget(
        &self,
        candidate_gpu_bytes: usize,
        candidate_cpu_bytes: usize,
        depth_bytes: usize,
    ) -> Result<usize, EngineError> {
        let budget = self.budget();
        let peak_gpu = self.gpu_buffer_allocated + candidate_gpu_bytes + depth_bytes;
        let peak_cpu = self.cpu_decoded_bytes + candidate_cpu_bytes;

        if peak_gpu > budget.gpu_resident_budget_bytes {
            return Err(EngineError::new(
                ErrorCode::MemoryLimit,
                format!(
                    "MEMORY_LIMIT: Pico de memoria GPU estimado ({} B) excede el presupuesto ({} B)",
                    peak_gpu, budget.gpu_resident_budget_bytes
                ),
                true,
            ));
        }

        if peak_cpu > budget.cpu_decoded_budget_bytes {
            return Err(EngineError::new(
                ErrorCode::MemoryLimit,
                format!(
                    "MEMORY_LIMIT: Pico de memoria CPU estimado ({} B) excede el presupuesto ({} B)",
                    peak_cpu, budget.cpu_decoded_budget_bytes
                ),
                true,
            ));
        }

        Ok(peak_gpu)
    }

    pub fn snapshot(&self, scene_revision: SceneRevision) -> MemoryStats {
        let budget = self.budget();
        let total_gpu_resident = self.gpu_buffer_allocated + self.gpu_depth_estimate;
        MemoryStats {
            resident_gpu_bytes: total_gpu_resident,
            decoded_cpu_bytes: self.cpu_decoded_bytes,
            cached_storage_bytes: self.cached_storage_bytes,
            evictions_count: self.evictions_count,
            current_generation: self.generation,
            active_request_id: self.active_request_id,
            scene_revision,
            quality_profile: self.profile,
            gpu_budget_bytes: budget.gpu_resident_budget_bytes,
            cpu_budget_bytes: budget.cpu_decoded_budget_bytes,

            gpu_buffer_allocated_estimate: self.gpu_buffer_allocated,
            gpu_depth_render_target_estimate: self.gpu_depth_estimate,
            resident_gpu_bytes_estimate: total_gpu_resident,
            cpu_scene_decoded_estimate: self.cpu_decoded_bytes,
            cpu_staging_bytes_estimate: self.cpu_staging_bytes,
            verified_blob_bytes: self.verified_blob_bytes,
            cache_storage_estimate: self.cached_storage_bytes,
            peak_overlap_bytes_estimate: self.peak_overlap_bytes,
            memory_budget_gpu_bytes: budget.gpu_resident_budget_bytes,
            memory_budget_cpu_bytes: budget.cpu_decoded_budget_bytes,
            is_within_budget: self.is_within_budget(),
        }
    }
}

pub fn calculate_scene_cpu_bytes(scene: &Scene) -> usize {
    let mut total = 0;
    // Calculate geometry bytes from meshes and primitives
    for mesh in &scene.meshes {
        if let Some(name) = &mesh.name {
            total += name.len();
        }
        total += std::mem::size_of_val(mesh);
        for prim in &mesh.primitives {
            total += prim.vertices.len() * std::mem::size_of::<crate::scene::Vertex>();
            total += prim.indices.len() * std::mem::size_of::<u32>();
            total += std::mem::size_of_val(prim);
        }
    }
    // Calculate node and hierarchy overhead
    for node in &scene.nodes {
        if let Some(name) = &node.name {
            total += name.len();
        }
        if let Some(id) = &node.anatomy_id {
            total += id.len();
        }
        total += node.children.len() * std::mem::size_of::<usize>();
        total += std::mem::size_of_val(node);
    }
    total
}

pub fn calculate_scene_gpu_bytes(scene: &Scene) -> usize {
    let mut total = 0;
    // Material uniforms
    total += scene.materials.len().max(1) * 256;
    // Mesh primitives (vertex + index buffers)
    for mesh in &scene.meshes {
        for prim in &mesh.primitives {
            total += prim.vertices.len() * std::mem::size_of::<crate::scene::Vertex>();
            total += prim.indices.len() * std::mem::size_of::<u32>();
        }
    }
    // Node object uniforms
    total += scene.nodes.len() * 256;
    total
}

pub fn calculate_gpu_resident_bytes(
    vertex_count: usize,
    index_count: usize,
    uniform_buffers_count: usize,
) -> usize {
    let vertex_bytes = vertex_count * std::mem::size_of::<crate::scene::Vertex>();
    let index_bytes = index_count * std::mem::size_of::<u32>();
    let uniform_bytes = uniform_buffers_count * 256; // typical aligned uniform buffer
    vertex_bytes + index_bytes + uniform_bytes
}
