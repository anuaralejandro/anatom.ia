use bytemuck::{Pod, Zeroable};
use glam::{Mat3, Mat4, Vec3};
use serde::{Deserialize, Serialize};

use crate::camera::Ray;
use crate::types::AnatomyId;

#[repr(C)]
#[derive(Clone, Copy, Debug, Pod, Zeroable, Serialize, Deserialize)]
pub struct Vertex {
    pub position: [f32; 3],
    pub normal: [f32; 3],
}

impl Vertex {
    pub fn desc<'a>() -> wgpu::VertexBufferLayout<'a> {
        wgpu::VertexBufferLayout {
            array_stride: std::mem::size_of::<Vertex>() as wgpu::BufferAddress,
            step_mode: wgpu::VertexStepMode::Vertex,
            attributes: &[
                wgpu::VertexAttribute {
                    offset: 0,
                    shader_location: 0,
                    format: wgpu::VertexFormat::Float32x3,
                },
                wgpu::VertexAttribute {
                    offset: 12,
                    shader_location: 1,
                    format: wgpu::VertexFormat::Float32x3,
                },
            ],
        }
    }
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct AABB {
    pub min: Vec3,
    pub max: Vec3,
}

impl Default for AABB {
    fn default() -> Self {
        Self {
            min: Vec3::splat(f32::INFINITY),
            max: Vec3::splat(f32::NEG_INFINITY),
        }
    }
}

impl AABB {
    pub fn new(min: Vec3, max: Vec3) -> Self {
        Self { min, max }
    }

    pub fn expand(&mut self, point: Vec3) {
        self.min = self.min.min(point);
        self.max = self.max.max(point);
    }

    pub fn union(&self, other: &AABB) -> AABB {
        AABB {
            min: self.min.min(other.min),
            max: self.max.max(other.max),
        }
    }

    pub fn center(&self) -> Vec3 {
        (self.min + self.max) * 0.5
    }

    pub fn size(&self) -> Vec3 {
        self.max - self.min
    }

    pub fn is_valid(&self) -> bool {
        self.min.x <= self.max.x && self.min.y <= self.max.y && self.min.z <= self.max.z
    }

    pub fn transform(&self, matrix: &Mat4) -> AABB {
        if !self.is_valid() {
            return *self;
        }
        let corners = [
            Vec3::new(self.min.x, self.min.y, self.min.z),
            Vec3::new(self.max.x, self.min.y, self.min.z),
            Vec3::new(self.min.x, self.max.y, self.min.z),
            Vec3::new(self.max.x, self.max.y, self.min.z),
            Vec3::new(self.min.x, self.min.y, self.max.z),
            Vec3::new(self.max.x, self.min.y, self.max.z),
            Vec3::new(self.min.x, self.max.y, self.max.z),
            Vec3::new(self.max.x, self.max.y, self.max.z),
        ];

        let mut result = AABB::default();
        for corner in corners {
            let transformed = matrix.transform_point3(corner);
            result.expand(transformed);
        }
        result
    }

    /// Robust slab intersection, including rays parallel to box planes.
    /// A parallel ray that starts outside any slab cannot hit the box.
    pub fn intersects_ray(&self, ray: &Ray) -> Option<f32> {
        if !self.is_valid() || !ray.origin.is_finite() || !ray.direction.is_finite() {
            return None;
        }
        let mut near = f32::NEG_INFINITY;
        let mut far = f32::INFINITY;
        for axis in 0..3 {
            let origin = ray.origin[axis];
            let direction = ray.direction[axis];
            let min = self.min[axis];
            let max = self.max[axis];

            if direction.abs() <= f32::EPSILON {
                if origin < min || origin > max {
                    return None;
                }
                continue;
            }
            let t0 = (min - origin) / direction;
            let t1 = (max - origin) / direction;
            near = near.max(t0.min(t1));
            far = far.min(t0.max(t1));
            if far < near {
                return None;
            }
        }
        if far < 0.0 {
            return None;
        }
        Some(near.max(0.0))
    }
}

#[derive(Debug, Clone)]
pub struct Material {
    pub name: Option<String>,
    pub base_color: [f32; 4],
    pub roughness: f32,
    pub metallic: f32,
    pub double_sided: bool,
}

impl Default for Material {
    fn default() -> Self {
        Self {
            name: None,
            base_color: [0.8, 0.8, 0.8, 1.0],
            roughness: 0.5,
            metallic: 0.0,
            double_sided: true,
        }
    }
}

#[derive(Debug, Clone)]
pub struct Primitive {
    pub vertices: Vec<Vertex>,
    pub indices: Vec<u32>,
    pub material_index: Option<usize>,
    pub bounds: AABB,
}

#[derive(Debug, Clone)]
pub struct Mesh {
    pub name: Option<String>,
    pub primitives: Vec<Primitive>,
}

#[derive(Debug, Clone)]
pub struct Node {
    pub name: Option<String>,
    pub anatomy_id: Option<AnatomyId>,
    pub mesh_index: Option<usize>,
    pub local_transform: Mat4,
    pub world_transform: Mat4,
    pub children: Vec<usize>,
    pub visible: bool,
}

#[derive(Debug, Clone, Default)]
pub struct Scene {
    pub nodes: Vec<Node>,
    pub meshes: Vec<Mesh>,
    pub materials: Vec<Material>,
    pub root_nodes: Vec<usize>,
    pub selected_id: Option<AnatomyId>,
    pub bounds: AABB,
    pub revision: u32,
}

impl Scene {
    pub fn update_world_transforms(&mut self) {
        let root_nodes = self.root_nodes.clone();
        for root_idx in root_nodes {
            let parent_tx = Mat4::IDENTITY;
            self.compute_world_transform(root_idx, &parent_tx);
        }
        self.recompute_bounds();
        self.revision += 1;
    }

    fn compute_world_transform(&mut self, node_idx: usize, parent_tx: &Mat4) {
        let world_tx = *parent_tx * self.nodes[node_idx].local_transform;
        self.nodes[node_idx].world_transform = world_tx;

        let children = self.nodes[node_idx].children.clone();
        for child_idx in children {
            self.compute_world_transform(child_idx, &world_tx);
        }
    }

    pub fn recompute_bounds(&mut self) {
        let mut overall = AABB::default();
        for node in &self.nodes {
            if let Some(mesh_idx) = node.mesh_index {
                let mesh = &self.meshes[mesh_idx];
                for prim in &mesh.primitives {
                    let prim_world_bounds = prim.bounds.transform(&node.world_transform);
                    overall = overall.union(&prim_world_bounds);
                }
            }
        }
        self.bounds = overall;
    }

    pub fn set_visibility(&mut self, id: &str, visible: bool) -> bool {
        let mut found = false;
        for node in &mut self.nodes {
            if node.anatomy_id.as_deref() == Some(id) {
                node.visible = visible;
                found = true;
            }
        }
        if found {
            self.revision += 1;
        }
        found
    }

    pub fn isolate_structure(&mut self, id: &str) -> bool {
        // Validate first; an unknown ID must not blank the complete atlas.
        if !self
            .nodes
            .iter()
            .any(|node| node.anatomy_id.as_deref() == Some(id))
        {
            return false;
        }
        let mut found = false;
        for node in &mut self.nodes {
            if let Some(ref aid) = node.anatomy_id {
                if aid == id {
                    node.visible = true;
                    found = true;
                } else {
                    node.visible = false;
                }
            }
        }
        if found {
            self.selected_id = Some(id.to_string());
            self.revision += 1;
        }
        found
    }

    pub fn reset_visibility(&mut self) {
        for node in &mut self.nodes {
            node.visible = true;
        }
        self.revision += 1;
    }

    pub fn select_structure(&mut self, id: Option<AnatomyId>) {
        self.selected_id = id;
        self.revision += 1;
    }

    pub fn get_structure_bounds(&self, id: &str) -> Option<AABB> {
        let mut bounds = AABB::default();
        let mut found = false;
        for node in &self.nodes {
            match (
                node.anatomy_id.as_deref(),
                node.mesh_index.and_then(|idx| self.meshes.get(idx)),
            ) {
                (Some(aid), Some(mesh)) if aid == id => {
                    for prim in &mesh.primitives {
                        let world_bounds = prim.bounds.transform(&node.world_transform);
                        bounds = bounds.union(&world_bounds);
                        found = true;
                    }
                }
                _ => {}
            }
        }
        if found && bounds.is_valid() {
            Some(bounds)
        } else {
            None
        }
    }

    pub fn get_visible_ids(&self) -> Vec<AnatomyId> {
        let mut set = Vec::new();
        for node in &self.nodes {
            if node.visible {
                match &node.anatomy_id {
                    Some(aid) if !set.contains(aid) => {
                        set.push(aid.clone());
                    }
                    _ => {}
                }
            }
        }
        set
    }

    pub fn normal_matrix_for(transform: &Mat4) -> Mat3 {
        let mat3 = Mat3::from_cols(
            transform.x_axis.truncate(),
            transform.y_axis.truncate(),
            transform.z_axis.truncate(),
        );
        mat3.inverse().transpose()
    }
}
