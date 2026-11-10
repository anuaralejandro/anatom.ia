use atlas_core::shader::SHADER_SOURCE;

#[test]
fn test_wgsl_shader_compilation_with_naga() {
    let module = naga::front::wgsl::parse_str(SHADER_SOURCE)
        .expect("WGSL shader source must parse cleanly without syntax errors");

    // Validate module
    let mut validator = naga::valid::Validator::new(
        naga::valid::ValidationFlags::all(),
        naga::valid::Capabilities::empty(), // Strict baseline capabilities (downlevel / WebGL2 friendly)
    );

    let info = validator.validate(&module).expect(
        "Shader module must pass strict validation without requiring advanced GPU capabilities",
    );

    // Verify entry points exist
    let vs = module
        .entry_points
        .iter()
        .find(|ep| ep.name == "vs_main" && ep.stage == naga::ShaderStage::Vertex);
    assert!(vs.is_some(), "vs_main vertex entry point must exist");

    let fs = module
        .entry_points
        .iter()
        .find(|ep| ep.name == "fs_main" && ep.stage == naga::ShaderStage::Fragment);
    assert!(fs.is_some(), "fs_main fragment entry point must exist");

    // Validate GLSL translation for WebGL2 fallback verification
    let glsl_options = naga::back::glsl::Options {
        version: naga::back::glsl::Version::Embedded {
            version: 300,
            is_webgl: true,
        },
        ..Default::default()
    };

    let mut glsl_out = String::new();
    let pipeline_options = naga::back::glsl::PipelineOptions {
        shader_stage: naga::ShaderStage::Vertex,
        entry_point: "vs_main".into(),
        multiview: None,
    };
    let mut writer = naga::back::glsl::Writer::new(
        &mut glsl_out,
        &module,
        &info,
        &glsl_options,
        &pipeline_options,
        naga::proc::BoundsCheckPolicies::default(),
    )
    .expect("GLSL writer creation must succeed");

    assert!(
        writer.write().is_ok(),
        "Shader vertex stage must be compilable to WebGL2 GLSL ES 3.00"
    );
}
