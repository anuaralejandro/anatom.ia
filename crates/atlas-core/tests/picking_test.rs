use std::fs;
use std::path::PathBuf;

use atlas_core::camera::{Camera, Ray};
use atlas_core::glb::parse_glb;
use atlas_core::picking::{pick_scene, ray_triangle_intersect};
use atlas_core::scene::AABB;
use glam::Vec3;

fn load_real_scene() -> atlas_core::scene::Scene {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let path = manifest_dir
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .join("reports")
        .join("experimental")
        .join("pelvis-pbr-core-compat.glb");
    let bytes = fs::read(&path).expect("Fixture GLB must exist");
    parse_glb(&bytes).expect("Fixture must parse cleanly")
}

#[test]
fn test_ray_triangle_math() {
    let v0 = Vec3::new(0.0, 0.0, 0.0);
    let v1 = Vec3::new(1.0, 0.0, 0.0);
    let v2 = Vec3::new(0.0, 1.0, 0.0);

    // Direct hit from +Z towards -Z
    let ray = Ray::new(Vec3::new(0.2, 0.2, 1.0), Vec3::new(0.0, 0.0, -1.0));
    let hit = ray_triangle_intersect(&ray, v0, v1, v2, false);
    assert!(hit.is_some());
    assert!((hit.unwrap() - 1.0).abs() < 1e-4);

    // Miss outside triangle
    let ray_miss = Ray::new(Vec3::new(2.0, 2.0, 1.0), Vec3::new(0.0, 0.0, -1.0));
    assert!(ray_triangle_intersect(&ray_miss, v0, v1, v2, false).is_none());

    // Hit from backface when two_sided is false
    let ray_back = Ray::new(Vec3::new(0.2, 0.2, -1.0), Vec3::new(0.0, 0.0, 1.0));
    assert!(ray_triangle_intersect(&ray_back, v0, v1, v2, false).is_none());

    // Hit from backface when two_sided is true
    let hit_back_two_sided = ray_triangle_intersect(&ray_back, v0, v1, v2, true);
    assert!(hit_back_two_sided.is_some());
    assert!((hit_back_two_sided.unwrap() - 1.0).abs() < 1e-4);
}

#[test]
fn test_aabb_ray_intersection() {
    let aabb = AABB::new(Vec3::new(-1.0, -1.0, -1.0), Vec3::new(1.0, 1.0, 1.0));

    // Direct hit
    let ray = Ray::new(Vec3::new(0.0, 0.0, 5.0), Vec3::new(0.0, 0.0, -1.0));
    let t = aabb.intersects_ray(&ray);
    assert!(t.is_some());
    assert!((t.unwrap() - 4.0).abs() < 1e-4);

    // Ray inside box -> t = 0.0
    let ray_inside = Ray::new(Vec3::new(0.0, 0.0, 0.0), Vec3::new(0.0, 0.0, 1.0));
    assert_eq!(aabb.intersects_ray(&ray_inside), Some(0.0));

    // Miss
    let ray_miss = Ray::new(Vec3::new(5.0, 5.0, 5.0), Vec3::new(0.0, 0.0, -1.0));
    assert!(aabb.intersects_ray(&ray_miss).is_none());
}

#[test]
fn test_scene_picking_and_occlusion() {
    let mut scene = load_real_scene();

    // Find center and bounds of Sacrum (ta2:1071)
    let sacrum_bounds = scene
        .get_structure_bounds("ta2:1071")
        .expect("Sacrum bounds must exist");
    let sacrum_center = sacrum_bounds.center();

    // Raycast towards Sacrum center from posterior direction (-Z in patient coords or from behind)
    let ray_from_behind = Ray::new(
        Vec3::new(sacrum_center.x, sacrum_center.y, sacrum_center.z - 2.0),
        Vec3::new(0.0, 0.0, 1.0),
    );

    let hit = pick_scene(&scene, &ray_from_behind);
    assert!(hit.is_some(), "Must hit a structure from behind Sacrum");

    // Test visibility filtering: hide all except Sacrum and verify only Sacrum is selectable
    scene.isolate_structure("ta2:1071");
    let hit_isolated = pick_scene(&scene, &ray_from_behind);
    assert_eq!(
        hit_isolated.map(|h| h.anatomy_id),
        Some("ta2:1071".to_string()),
        "Isolated Sacrum must be picked"
    );

    // Hide Sacrum: now pick must return None because it is hidden
    scene.set_visibility("ta2:1071", false);
    let hit_hidden = pick_scene(&scene, &ray_from_behind);
    assert!(
        hit_hidden.is_none(),
        "Hidden Sacrum must not be picked by ray"
    );

    // Reset visibility
    scene.reset_visibility();
    assert_eq!(scene.get_visible_ids().len(), 26);
}

#[test]
fn test_camera_controls_and_bounds_fit() {
    let scene = load_real_scene();
    let mut camera = Camera::default();

    camera.fit_bounds(scene.bounds.min, scene.bounds.max);
    assert!(camera.distance > 0.0);
    assert!(camera.distance < 5.0);

    let initial_dist = camera.distance;
    camera.zoom(10.0);
    assert!(
        camera.distance > initial_dist,
        "Zooming in/out must change distance"
    );

    let initial_yaw = camera.yaw;
    camera.orbit(10.0, 0.0);
    assert_ne!(camera.yaw, initial_yaw, "Orbit must change yaw");

    // Ray from screen center
    let ray_center = camera.ray_from_screen(400.0, 300.0, 800.0, 600.0);
    assert!(ray_center.direction.is_normalized());
}

#[test]
fn test_unknown_isolate_does_not_hide_scene() {
    let mut scene = load_real_scene();
    assert_eq!(scene.get_visible_ids().len(), 26);
    assert!(!scene.isolate_structure("ta2:not-present"));
    assert_eq!(
        scene.get_visible_ids().len(),
        26,
        "Unknown IDs must not blank the atlas"
    );
}

#[test]
fn test_parallel_aabb_rays_on_faces_and_edges() {
    let b = AABB::new(Vec3::splat(-1.0), Vec3::splat(1.0));
    // A ray parallel to two slab faces must be rejected when outside either slab.
    assert_eq!(
        b.intersects_ray(&Ray::new(Vec3::new(2.0, 0.0, 5.0), Vec3::NEG_Z)),
        None
    );
    // Starting precisely on a slab plane is a valid hit, not NaN from 0/0.
    assert_eq!(
        b.intersects_ray(&Ray::new(Vec3::new(1.0, 0.0, 5.0), Vec3::NEG_Z)),
        Some(4.0)
    );
    assert_eq!(
        b.intersects_ray(&Ray::new(Vec3::new(1.0, 1.0, 0.0), Vec3::Z)),
        Some(0.0)
    );
    // All components zero has no meaningful ray direction, but must not panic.
    assert!(
        b.intersects_ray(&Ray::new(Vec3::new(2.0, 0.0, 0.0), Vec3::ZERO))
            .is_none()
    );
}
