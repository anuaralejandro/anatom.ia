use serde::{Deserialize, Serialize};

use crate::scene::Scene;
use crate::types::{RequestId, SceneGeneration, SceneRevision};

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

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct MemoryStats {
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
}

#[derive(Debug, Clone)]
pub struct MemoryTracker {
    profile: QualityProfile,
    resident_gpu_bytes: usize,
    decoded_cpu_bytes: usize,
    cached_storage_bytes: usize,
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
            resident_gpu_bytes: 0,
            decoded_cpu_bytes: 0,
            cached_storage_bytes: 0,
            evictions_count: 0,
            generation: 1,
            active_request_id: None,
        }
    }

    pub fn set_profile(&mut self, profile: QualityProfile) {
        self.profile = profile;
    }

    pub fn profile(&self) -> QualityProfile {
        self.profile
    }

    pub fn set_resident_gpu_bytes(&mut self, bytes: usize) {
        self.resident_gpu_bytes = bytes;
    }

    pub fn set_decoded_cpu_bytes(&mut self, bytes: usize) {
        self.decoded_cpu_bytes = bytes;
    }

    pub fn set_cached_storage_bytes(&mut self, bytes: usize) {
        self.cached_storage_bytes = bytes;
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
        let budget = self.profile.budget();
        self.resident_gpu_bytes <= budget.gpu_resident_budget_bytes
            && self.decoded_cpu_bytes <= budget.cpu_decoded_budget_bytes
    }

    pub fn snapshot(&self, scene_revision: SceneRevision) -> MemoryStats {
        let budget = self.profile.budget();
        MemoryStats {
            resident_gpu_bytes: self.resident_gpu_bytes,
            decoded_cpu_bytes: self.decoded_cpu_bytes,
            cached_storage_bytes: self.cached_storage_bytes,
            evictions_count: self.evictions_count,
            current_generation: self.generation,
            active_request_id: self.active_request_id,
            scene_revision,
            quality_profile: self.profile,
            gpu_budget_bytes: budget.gpu_resident_budget_bytes,
            cpu_budget_bytes: budget.cpu_decoded_budget_bytes,
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
