// anatom.ia — Core Anatomy WGSL Shader v1
// Strictly compliant with WebGPU and WebGL2 (downlevel_webgl2_defaults).
// NO storage buffers, NO compute, NO push constants, NO indirect draw.
// NO @interpolate(linear) / noperspective interpolation.

struct CameraUniform {
    view_proj: mat4x4<f32>,
    camera_pos: vec3<f32>,
    _pad0: f32,
};

struct ObjectUniform {
    model: mat4x4<f32>,
    normal_col0: vec4<f32>,
    normal_col1: vec4<f32>,
    normal_col2: vec4<f32>,
    is_selected: u32,
    _pad0: u32,
    _pad1: u32,
    _pad2: u32,
};

struct MaterialUniform {
    base_color: vec4<f32>,
    roughness: f32,
    metallic: f32,
    opacity: f32,
    _pad0: f32,
};

@group(0) @binding(0)
var<uniform> camera: CameraUniform;

@group(1) @binding(0)
var<uniform> object: ObjectUniform;

@group(2) @binding(0)
var<uniform> material: MaterialUniform;

struct VertexInput {
    @location(0) position: vec3<f32>,
    @location(1) normal: vec3<f32>,
};

struct VertexOutput {
    @builtin(position) clip_position: vec4<f32>,
    @location(0) world_normal: vec3<f32>,
    @location(1) world_position: vec3<f32>,
};

@vertex
fn vs_main(in: VertexInput) -> VertexOutput {
    var out: VertexOutput;
    let world_pos4 = object.model * vec4<f32>(in.position, 1.0);
    out.world_position = world_pos4.xyz;
    out.clip_position = camera.view_proj * world_pos4;

    // Normal matrix 3x3 from 3 columns
    let n_mat = mat3x3<f32>(
        object.normal_col0.xyz,
        object.normal_col1.xyz,
        object.normal_col2.xyz,
    );
    out.world_normal = normalize(n_mat * in.normal);
    return out;
}

@fragment
fn fs_main(in: VertexOutput) -> @location(0) vec4<f32> {
    var N = normalize(in.world_normal);
    let V = normalize(camera.camera_pos - in.world_position);

    // Two-sided lighting fallback: flip normal if viewing backface
    if (dot(N, V) < 0.0) {
        N = -N;
    }

    // Anatomical studio 2-point directional lighting + ambient
    let key_dir = normalize(vec3<f32>(0.4, 0.8, 0.6));
    let fill_dir = normalize(vec3<f32>(-0.4, -0.2, -0.6));

    let n_dot_l_key = max(dot(N, key_dir), 0.0);
    let n_dot_l_fill = max(dot(N, fill_dir), 0.0);

    let ambient = 0.28;
    let key_intensity = 0.62;
    let fill_intensity = 0.20;

    let lighting = ambient + key_intensity * n_dot_l_key + fill_intensity * n_dot_l_fill;

    // Specular highlight (Blinn-Phong)
    let H_key = normalize(key_dir + V);
    let spec = pow(max(dot(N, H_key), 0.0), 32.0) * (1.0 - material.roughness) * 0.3;

    var color = material.base_color.rgb * lighting + vec3<f32>(spec);

    // Selection highlight: turquoise tint overlay if is_selected == 1
    if (object.is_selected == 1u) {
        let highlight_tint = vec3<f32>(0.0, 0.85, 0.95);
        color = mix(color, highlight_tint, 0.45) + highlight_tint * 0.2;
    }

    return vec4<f32>(color, material.base_color.a * material.opacity);
}
