use atlas_core::scene::{AABB, Mesh, Node, Primitive, Scene, Vertex};
use glam::{Mat4, Vec3};

fn create_test_node(id: &str, name: &str, mesh_idx: usize) -> Node {
    Node {
        name: Some(name.to_string()),
        anatomy_id: Some(id.to_string()),
        mesh_index: Some(mesh_idx),
        local_transform: Mat4::IDENTITY,
        world_transform: Mat4::IDENTITY,
        children: vec![],
        visible: true,
    }
}

fn create_test_primitive() -> Primitive {
    Primitive {
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
        material_index: Some(0),
        bounds: AABB::new(Vec3::ZERO, Vec3::ONE),
    }
}

fn create_sample_scene() -> Scene {
    let mut scene = Scene::default();
    scene.materials.push(atlas_core::scene::Material::default());
    scene.meshes.push(Mesh {
        name: Some("test_mesh".to_string()),
        primitives: vec![create_test_primitive()],
    });
    scene
        .nodes
        .push(create_test_node("ta2:sacrum", "Sacrum", 0));
    scene
        .nodes
        .push(create_test_node("ta2:ilium:left", "Left Ilium", 0));
    scene
        .nodes
        .push(create_test_node("ta2:ilium:right", "Right Ilium", 0));
    scene
}

#[test]
fn test_atomic_swap_preserves_selection_and_visibility() {
    let mut scene_a = create_sample_scene();
    scene_a.select_structure(Some("ta2:sacrum".to_string()));
    scene_a.set_visibility("ta2:ilium:left", false);

    assert_eq!(scene_a.selected_id.as_deref(), Some("ta2:sacrum"));
    assert!(!scene_a.nodes[1].visible);
    assert!(scene_a.nodes[0].visible);
    assert!(scene_a.nodes[2].visible);

    let mut scene_b = create_sample_scene();
    // Scene B starts default (all visible, no selection)
    assert_eq!(scene_b.selected_id, None);
    assert!(scene_b.nodes[1].visible);

    // Swap / Transfer state
    scene_b.transfer_state_from(&scene_a);

    assert_eq!(scene_b.selected_id.as_deref(), Some("ta2:sacrum"));
    assert!(scene_b.nodes[0].visible);
    assert!(!scene_b.nodes[1].visible);
    assert!(scene_b.nodes[2].visible);
    assert_eq!(scene_b.revision, scene_a.revision + 1);
}

#[test]
fn test_atomic_swap_preserves_isolated_structure() {
    let mut scene_a = create_sample_scene();
    assert!(scene_a.isolate_structure("ta2:sacrum"));

    // Verify isolation in scene_a
    assert_eq!(scene_a.selected_id.as_deref(), Some("ta2:sacrum"));
    assert!(scene_a.nodes[0].visible);
    assert!(!scene_a.nodes[1].visible);
    assert!(!scene_a.nodes[2].visible);

    let mut scene_b = create_sample_scene();
    scene_b.transfer_state_from(&scene_a);

    assert_eq!(scene_b.selected_id.as_deref(), Some("ta2:sacrum"));
    assert!(scene_b.nodes[0].visible);
    assert!(!scene_b.nodes[1].visible);
    assert!(!scene_b.nodes[2].visible);
    assert_eq!(scene_b.revision, scene_a.revision + 1);
}

#[test]
fn test_atomic_swap_missing_selected_id_safely_drops() {
    let mut scene_a = create_sample_scene();
    scene_a.select_structure(Some("ta2:femur:left".to_string()));

    let mut scene_b = create_sample_scene();
    scene_b.transfer_state_from(&scene_a);

    // Since femur:left does not exist in scene_b, selection should be None
    assert_eq!(scene_b.selected_id, None);
}

#[test]
fn test_transactional_swap_commit_rollback_lifecycle() {
    let mut res_a = atlas_core::renderer::GpuSceneResources::empty();
    res_a.resident_geometry_gpu_bytes = 1000;

    let mut res_b = atlas_core::renderer::GpuSceneResources::empty();
    res_b.resident_geometry_gpu_bytes = 2000;

    // Simulate renderer container holding active resources
    let mut active = Some(res_a);

    // Commit Phase
    let mut retiring = active.take();
    active = Some(res_b);
    assert_eq!(active.as_ref().unwrap().resident_geometry_gpu_bytes, 2000);
    assert_eq!(retiring.as_ref().unwrap().resident_geometry_gpu_bytes, 1000);

    // Rollback Phase (e.g. if first frame render fails)
    let failed = active.take();
    drop(failed);
    active = retiring.take();
    assert_eq!(active.as_ref().unwrap().resident_geometry_gpu_bytes, 1000);
    assert!(retiring.is_none());
}
