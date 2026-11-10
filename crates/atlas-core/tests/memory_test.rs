use atlas_core::memory::{
    MemoryTracker, QualityProfile, calculate_gpu_resident_bytes, calculate_scene_cpu_bytes,
};
use atlas_core::scene::{Mesh, Node, Primitive, Scene, Vertex};

#[test]
fn test_quality_profile_budgets() {
    let low = QualityProfile::Low.budget();
    assert_eq!(low.gpu_resident_budget_bytes, 64 * 1024 * 1024);
    assert_eq!(low.cpu_decoded_budget_bytes, 48 * 1024 * 1024);
    assert_eq!(low.concurrent_fetches, 2);

    let med = QualityProfile::Medium.budget();
    assert_eq!(med.gpu_resident_budget_bytes, 128 * 1024 * 1024);
    assert_eq!(med.cpu_decoded_budget_bytes, 96 * 1024 * 1024);
    assert_eq!(med.concurrent_fetches, 3);

    let high = QualityProfile::High.budget();
    assert_eq!(high.gpu_resident_budget_bytes, 256 * 1024 * 1024);
    assert_eq!(high.cpu_decoded_budget_bytes, 160 * 1024 * 1024);
    assert_eq!(high.concurrent_fetches, 4);
}

#[test]
fn test_memory_tracker_lifecycle() {
    let mut tracker = MemoryTracker::new(QualityProfile::Low);
    assert_eq!(tracker.current_generation(), 1);

    tracker.set_resident_gpu_bytes(10 * 1024 * 1024);
    tracker.set_decoded_cpu_bytes(8 * 1024 * 1024);
    assert!(tracker.is_within_budget());

    // Advance generation with request_id
    let gen2 = tracker.next_generation(Some(101));
    assert_eq!(gen2, 2);
    assert_eq!(tracker.current_generation(), 2);

    // Eviction tracking
    tracker.record_eviction();
    tracker.record_eviction();

    let snap = tracker.snapshot(42);
    assert_eq!(snap.current_generation, 2);
    assert_eq!(snap.active_request_id, Some(101));
    assert_eq!(snap.evictions_count, 2);
    assert_eq!(snap.scene_revision, 42);
    assert_eq!(snap.resident_gpu_bytes, 10 * 1024 * 1024);
    assert_eq!(snap.decoded_cpu_bytes, 8 * 1024 * 1024);
    assert_eq!(snap.quality_profile, QualityProfile::Low);

    // Exceed budget
    tracker.set_resident_gpu_bytes(70 * 1024 * 1024);
    assert!(!tracker.is_within_budget());
}

#[test]
fn test_calculate_scene_memory() {
    let mut scene = Scene::default();
    let prim = Primitive {
        vertices: vec![
            Vertex {
                position: [0.0, 0.0, 0.0],
                normal: [0.0, 1.0, 0.0],
            },
            Vertex {
                position: [1.0, 0.0, 0.0],
                normal: [0.0, 1.0, 0.0],
            },
            Vertex {
                position: [0.0, 1.0, 0.0],
                normal: [0.0, 1.0, 0.0],
            },
        ],
        indices: vec![0, 1, 2],
        material_index: None,
        bounds: Default::default(),
    };

    scene.meshes.push(Mesh {
        name: Some("test_mesh".to_string()),
        primitives: vec![prim],
    });

    scene.nodes.push(Node {
        name: Some("test_node".to_string()),
        anatomy_id: Some("ta2:1071".to_string()),
        mesh_index: Some(0),
        local_transform: glam::Mat4::IDENTITY,
        world_transform: glam::Mat4::IDENTITY,
        children: vec![],
        visible: true,
    });

    let cpu_bytes = calculate_scene_cpu_bytes(&scene);
    assert!(cpu_bytes > 0);

    let gpu_bytes = calculate_gpu_resident_bytes(3, 3, 1);
    assert_eq!(
        gpu_bytes,
        (3 * std::mem::size_of::<atlas_core::scene::Vertex>()) + (3 * 4) + 256
    );
}

#[test]
fn test_preflight_swap_budget_enforcement() {
    let mut tracker = MemoryTracker::new(QualityProfile::Low);
    tracker.set_resident_gpu_bytes(10 * 1024 * 1024);
    tracker.set_decoded_cpu_bytes(5 * 1024 * 1024);

    // Normal swap fits easily within Low budget (64 MiB GPU, 48 MiB CPU)
    let res = tracker.preflight_swap_budget(5 * 1024 * 1024, 4 * 1024 * 1024, 2 * 1024 * 1024);
    assert!(res.is_ok());

    // Excessive GPU swap allocation exceeds 64 MiB
    let res_gpu_excess =
        tracker.preflight_swap_budget(60 * 1024 * 1024, 4 * 1024 * 1024, 2 * 1024 * 1024);
    assert!(res_gpu_excess.is_err());
    let err = res_gpu_excess.unwrap_err();
    assert_eq!(err.code, atlas_core::types::ErrorCode::MemoryLimit);
    assert!(err.recoverable);

    // Excessive CPU allocation exceeds 48 MiB
    let res_cpu_excess =
        tracker.preflight_swap_budget(5 * 1024 * 1024, 45 * 1024 * 1024, 2 * 1024 * 1024);
    assert!(res_cpu_excess.is_err());
    let err = res_cpu_excess.unwrap_err();
    assert_eq!(err.code, atlas_core::types::ErrorCode::MemoryLimit);
}

#[test]
fn test_custom_test_budget() {
    let mut tracker = MemoryTracker::new(QualityProfile::Medium);
    tracker.set_resident_gpu_bytes(2 * 1024 * 1024);
    tracker.set_decoded_cpu_bytes(2 * 1024 * 1024);

    // Default Medium allows 128 MB GPU
    assert!(
        tracker
            .preflight_swap_budget(2 * 1024 * 1024, 2 * 1024 * 1024, 1024 * 1024)
            .is_ok()
    );

    // Set artificial tight budget (e.g. 3 MB GPU, 3 MB CPU)
    tracker.set_custom_budget(Some(atlas_core::memory::MemoryBudget {
        gpu_resident_budget_bytes: 3 * 1024 * 1024,
        cpu_decoded_budget_bytes: 3 * 1024 * 1024,
        concurrent_fetches: 2,
    }));

    // Now 2MB active + 2MB candidate + 1MB depth = 5MB > 3MB budget -> rejected!
    let res = tracker.preflight_swap_budget(2 * 1024 * 1024, 2 * 1024 * 1024, 1024 * 1024);
    assert!(res.is_err());
    let err = res.unwrap_err();
    assert_eq!(err.code, atlas_core::types::ErrorCode::MemoryLimit);

    // Resetting quality profile clears custom budget
    tracker.set_profile(QualityProfile::High);
    assert!(
        tracker
            .preflight_swap_budget(2 * 1024 * 1024, 2 * 1024 * 1024, 1024 * 1024)
            .is_ok()
    );
}
