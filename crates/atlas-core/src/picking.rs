use glam::Vec3;

use crate::camera::Ray;
use crate::scene::Scene;
use crate::types::AnatomyId;

#[derive(Debug, Clone)]
pub struct HitResult {
    pub anatomy_id: AnatomyId,
    pub distance: f32,
    pub point: Vec3,
    pub node_index: usize,
}

/// Möller–Trumbore ray-triangle intersection algorithm.
/// Returns distance `t` along ray if intersection occurs and `t > 0.0`.
pub fn ray_triangle_intersect(
    ray: &Ray,
    v0: Vec3,
    v1: Vec3,
    v2: Vec3,
    two_sided: bool,
) -> Option<f32> {
    const EPSILON: f32 = 1e-7;

    let edge1 = v1 - v0;
    let edge2 = v2 - v0;
    let h = ray.direction.cross(edge2);
    let a = edge1.dot(h);

    if !two_sided {
        if a < EPSILON {
            return None; // Backface or parallel
        }
    } else {
        if a.abs() < EPSILON {
            return None; // Parallel
        }
    }

    let f = 1.0 / a;
    let s = ray.origin - v0;
    let u = f * s.dot(h);

    if !(0.0..=1.0).contains(&u) {
        return None;
    }

    let q = s.cross(edge1);
    let v = f * ray.direction.dot(q);

    if v < 0.0 || (u + v) > 1.0 {
        return None;
    }

    let t = f * edge2.dot(q);
    if t > EPSILON { Some(t) } else { None }
}

pub fn pick_scene(scene: &Scene, ray: &Ray) -> Option<HitResult> {
    let mut closest_hit: Option<HitResult> = None;

    for (node_idx, node) in scene.nodes.iter().enumerate() {
        if !node.visible {
            continue;
        }

        let anatomy_id = match &node.anatomy_id {
            Some(id) => id.clone(),
            None => continue,
        };

        let mesh_idx = match node.mesh_index {
            Some(idx) => idx,
            None => continue,
        };

        let mesh = match scene.meshes.get(mesh_idx) {
            Some(m) => m,
            None => continue,
        };

        // Broad-phase: AABB test in world space
        let mut node_world_aabb = crate::scene::AABB::default();
        for prim in &mesh.primitives {
            let prim_bounds = prim.bounds.transform(&node.world_transform);
            node_world_aabb = node_world_aabb.union(&prim_bounds);
        }

        if !node_world_aabb.is_valid() {
            continue;
        }

        let aabb_hit = node_world_aabb.intersects_ray(ray);
        if aabb_hit.is_none() {
            continue;
        }

        let box_t = aabb_hit.unwrap();
        if closest_hit.as_ref().is_some_and(|c| box_t > c.distance) {
            // Cannot possibly beat the current closest hit
            continue;
        }

        // Narrow-phase: transform ray to node's local coordinate space
        let inv_world = node.world_transform.inverse();
        let local_origin = inv_world.transform_point3(ray.origin);
        let local_target = inv_world.transform_point3(ray.origin + ray.direction);
        let local_dir = (local_target - local_origin).normalize();
        let local_ray = Ray::new(local_origin, local_dir);

        for prim in &mesh.primitives {
            let two_sided = prim
                .material_index
                .and_then(|idx| scene.materials.get(idx))
                .map(|m| m.double_sided)
                .unwrap_or(true);

            let indices = &prim.indices;
            let vertices = &prim.vertices;

            for chunk in indices.chunks_exact(3) {
                let i0 = chunk[0] as usize;
                let i1 = chunk[1] as usize;
                let i2 = chunk[2] as usize;

                let v0 = Vec3::from_slice(&vertices[i0].position);
                let v1 = Vec3::from_slice(&vertices[i1].position);
                let v2 = Vec3::from_slice(&vertices[i2].position);

                if let Some(t_local) = ray_triangle_intersect(&local_ray, v0, v1, v2, two_sided) {
                    let hit_point_local = local_ray.point_at(t_local);
                    let hit_point_world = node.world_transform.transform_point3(hit_point_local);
                    let dist_world = (hit_point_world - ray.origin).dot(ray.direction);

                    if dist_world > 0.0 {
                        let is_closer = match &closest_hit {
                            None => true,
                            Some(current) => dist_world < current.distance,
                        };

                        if is_closer {
                            closest_hit = Some(HitResult {
                                anatomy_id: anatomy_id.clone(),
                                distance: dist_world,
                                point: hit_point_world,
                                node_index: node_idx,
                            });
                        }
                    }
                }
            }
        }
    }

    closest_hit
}
