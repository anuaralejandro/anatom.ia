pub const SHADER_SOURCE: &str = include_str!("../../../shaders/anatomy_opaque.wgsl");

/// Validates that the WGSL shader compiles cleanly under Naga / wgpu.
pub fn validate_shader(device: &wgpu::Device) -> Result<wgpu::ShaderModule, String> {
    let sm = device.create_shader_module(wgpu::ShaderModuleDescriptor {
        label: Some("anatomy_opaque_shader"),
        source: wgpu::ShaderSource::Wgsl(SHADER_SOURCE.into()),
    });
    Ok(sm)
}
