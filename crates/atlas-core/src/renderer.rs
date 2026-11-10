use bytemuck::{Pod, Zeroable};
use glam::Mat4;
use wgpu::util::DeviceExt;

use crate::camera::Camera;
use crate::scene::{Material, Scene, Vertex};
use crate::shader::SHADER_SOURCE;
use crate::types::EngineCapabilities;

#[repr(C)]
#[derive(Clone, Copy, Debug, Pod, Zeroable)]
pub struct CameraUniform {
    pub view_proj: [f32; 16],
    pub camera_pos: [f32; 3],
    pub _pad0: f32,
}

#[repr(C)]
#[derive(Clone, Copy, Debug, Pod, Zeroable)]
pub struct ObjectUniform {
    pub model: [f32; 16],
    pub normal_col0: [f32; 4],
    pub normal_col1: [f32; 4],
    pub normal_col2: [f32; 4],
    pub is_selected: u32,
    pub _pad0: u32,
    pub _pad1: u32,
    pub _pad2: u32,
}

#[repr(C)]
#[derive(Clone, Copy, Debug, Pod, Zeroable)]
pub struct MaterialUniform {
    pub base_color: [f32; 4],
    pub roughness: f32,
    pub metallic: f32,
    pub opacity: f32,
    pub _pad0: f32,
}

pub struct GpuPrimitive {
    pub vertex_buffer: wgpu::Buffer,
    pub index_buffer: wgpu::Buffer,
    pub index_count: u32,
    pub material_index: usize,
}

pub struct GpuMesh {
    pub primitives: Vec<GpuPrimitive>,
}

pub struct GpuNode {
    pub object_buffer: wgpu::Buffer,
    pub object_bind_group: wgpu::BindGroup,
    pub mesh_index: Option<usize>,
}

pub struct GpuMaterial {
    pub uniform_buffer: wgpu::Buffer,
    pub bind_group: wgpu::BindGroup,
}

pub struct Renderer {
    pub device: wgpu::Device,
    pub queue: wgpu::Queue,
    pub pipeline: wgpu::RenderPipeline,

    pub camera_bind_group_layout: wgpu::BindGroupLayout,
    pub object_bind_group_layout: wgpu::BindGroupLayout,
    pub material_bind_group_layout: wgpu::BindGroupLayout,

    pub camera_buffer: wgpu::Buffer,
    pub camera_bind_group: wgpu::BindGroup,

    pub gpu_meshes: Vec<GpuMesh>,
    pub gpu_nodes: Vec<GpuNode>,
    pub gpu_materials: Vec<GpuMaterial>,

    pub depth_texture_view: wgpu::TextureView,
    pub depth_format: wgpu::TextureFormat,

    pub surface_format: wgpu::TextureFormat,
    pub width: u32,
    pub height: u32,
    pub clear_color: wgpu::Color,

    pub capabilities: EngineCapabilities,
    pub resident_gpu_bytes: usize,
}

impl Renderer {
    pub fn new(
        device: wgpu::Device,
        queue: wgpu::Queue,
        surface_format: wgpu::TextureFormat,
        width: u32,
        height: u32,
        capabilities: EngineCapabilities,
    ) -> Self {
        let depth_format = wgpu::TextureFormat::Depth24Plus;

        // Bind group layouts
        let camera_bind_group_layout =
            device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
                label: Some("camera_bind_group_layout"),
                entries: &[wgpu::BindGroupLayoutEntry {
                    binding: 0,
                    visibility: wgpu::ShaderStages::VERTEX | wgpu::ShaderStages::FRAGMENT,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Uniform,
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                }],
            });

        let object_bind_group_layout =
            device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
                label: Some("object_bind_group_layout"),
                entries: &[wgpu::BindGroupLayoutEntry {
                    binding: 0,
                    visibility: wgpu::ShaderStages::VERTEX | wgpu::ShaderStages::FRAGMENT,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Uniform,
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                }],
            });

        let material_bind_group_layout =
            device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
                label: Some("material_bind_group_layout"),
                entries: &[wgpu::BindGroupLayoutEntry {
                    binding: 0,
                    visibility: wgpu::ShaderStages::FRAGMENT,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Uniform,
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                }],
            });

        // Pipeline layout
        let pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
            label: Some("render_pipeline_layout"),
            bind_group_layouts: &[
                Some(&camera_bind_group_layout),
                Some(&object_bind_group_layout),
                Some(&material_bind_group_layout),
            ],
            immediate_size: 0,
        });

        // Shader module
        let shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("anatomy_opaque_shader"),
            source: wgpu::ShaderSource::Wgsl(SHADER_SOURCE.into()),
        });

        // Pipeline
        let pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("anatomy_opaque_pipeline"),
            layout: Some(&pipeline_layout),
            vertex: wgpu::VertexState {
                module: &shader,
                entry_point: Some("vs_main"),
                buffers: &[Some(Vertex::desc())],
                compilation_options: Default::default(),
            },
            fragment: Some(wgpu::FragmentState {
                module: &shader,
                entry_point: Some("fs_main"),
                targets: &[Some(wgpu::ColorTargetState {
                    format: surface_format,
                    blend: Some(wgpu::BlendState::ALPHA_BLENDING),
                    write_mask: wgpu::ColorWrites::ALL,
                })],
                compilation_options: Default::default(),
            }),
            primitive: wgpu::PrimitiveState {
                topology: wgpu::PrimitiveTopology::TriangleList,
                strip_index_format: None,
                front_face: wgpu::FrontFace::Ccw,
                cull_mode: None, // double-sided per initial contract
                unclipped_depth: false,
                polygon_mode: wgpu::PolygonMode::Fill,
                conservative: false,
            },
            depth_stencil: Some(wgpu::DepthStencilState {
                format: depth_format,
                depth_write_enabled: Some(true),
                depth_compare: Some(wgpu::CompareFunction::Less),
                stencil: wgpu::StencilState::default(),
                bias: wgpu::DepthBiasState::default(),
            }),
            multisample: wgpu::MultisampleState {
                count: 1,
                mask: !0,
                alpha_to_coverage_enabled: false,
            },
            multiview_mask: None,
            cache: None,
        });

        // Camera uniform buffer & bind group
        let camera_uniform = CameraUniform {
            view_proj: Mat4::IDENTITY.to_cols_array(),
            camera_pos: [0.0, 0.0, 1.0],
            _pad0: 0.0,
        };

        let camera_buffer = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("camera_buffer"),
            contents: bytemuck::cast_slice(&[camera_uniform]),
            usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
        });

        let camera_bind_group = device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("camera_bind_group"),
            layout: &camera_bind_group_layout,
            entries: &[wgpu::BindGroupEntry {
                binding: 0,
                resource: camera_buffer.as_entire_binding(),
            }],
        });

        // Depth texture
        let depth_texture_view = Self::create_depth_texture(&device, width, height, depth_format);

        Self {
            device,
            queue,
            pipeline,
            camera_bind_group_layout,
            object_bind_group_layout,
            material_bind_group_layout,
            camera_buffer,
            camera_bind_group,
            gpu_meshes: Vec::new(),
            gpu_nodes: Vec::new(),
            gpu_materials: Vec::new(),
            depth_texture_view,
            depth_format,
            surface_format,
            width,
            height,
            clear_color: wgpu::Color {
                r: 0.09,
                g: 0.10,
                b: 0.13,
                a: 1.0,
            },
            capabilities,
            resident_gpu_bytes: 0,
        }
    }

    fn create_depth_texture(
        device: &wgpu::Device,
        width: u32,
        height: u32,
        format: wgpu::TextureFormat,
    ) -> wgpu::TextureView {
        let size = wgpu::Extent3d {
            width: width.max(1),
            height: height.max(1),
            depth_or_array_layers: 1,
        };
        let desc = wgpu::TextureDescriptor {
            label: Some("depth_texture"),
            size,
            mip_level_count: 1,
            sample_count: 1,
            dimension: wgpu::TextureDimension::D2,
            format,
            usage: wgpu::TextureUsages::RENDER_ATTACHMENT,
            view_formats: &[],
        };
        let texture = device.create_texture(&desc);
        texture.create_view(&wgpu::TextureViewDescriptor::default())
    }

    pub fn resize(&mut self, width: u32, height: u32) {
        if width > 0 && height > 0 {
            self.width = width;
            self.height = height;
            self.depth_texture_view =
                Self::create_depth_texture(&self.device, width, height, self.depth_format);
        }
    }

    pub fn set_clear_color(&mut self, r: f64, g: f64, b: f64) {
        self.clear_color = wgpu::Color { r, g, b, a: 1.0 };
    }

    /// Releases GPU vertex, index, object, and material buffers explicitly.
    pub fn destroy_gpu_resources(&mut self) {
        for mesh in &self.gpu_meshes {
            for prim in &mesh.primitives {
                prim.vertex_buffer.destroy();
                prim.index_buffer.destroy();
            }
        }
        for node in &self.gpu_nodes {
            node.object_buffer.destroy();
        }
        for mat in &self.gpu_materials {
            mat.uniform_buffer.destroy();
        }
        self.gpu_meshes.clear();
        self.gpu_nodes.clear();
        self.gpu_materials.clear();
        self.resident_gpu_bytes = 0;
    }

    pub fn upload_scene(&mut self, scene: &Scene) {
        self.destroy_gpu_resources();

        let mut gpu_bytes = 0usize;

        // 1. Upload materials
        for mat in &scene.materials {
            let uniform = MaterialUniform {
                base_color: mat.base_color,
                roughness: mat.roughness,
                metallic: mat.metallic,
                opacity: 1.0,
                _pad0: 0.0,
            };

            let uniform_buffer =
                self.device
                    .create_buffer_init(&wgpu::util::BufferInitDescriptor {
                        label: Some("material_uniform_buffer"),
                        contents: bytemuck::cast_slice(&[uniform]),
                        usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
                    });

            gpu_bytes += std::mem::size_of::<MaterialUniform>();

            let bind_group = self.device.create_bind_group(&wgpu::BindGroupDescriptor {
                label: Some("material_bind_group"),
                layout: &self.material_bind_group_layout,
                entries: &[wgpu::BindGroupEntry {
                    binding: 0,
                    resource: uniform_buffer.as_entire_binding(),
                }],
            });

            self.gpu_materials.push(GpuMaterial {
                uniform_buffer,
                bind_group,
            });
        }

        // If no materials, create default
        if self.gpu_materials.is_empty() {
            let default_mat = Material::default();
            let uniform = MaterialUniform {
                base_color: default_mat.base_color,
                roughness: default_mat.roughness,
                metallic: default_mat.metallic,
                opacity: 1.0,
                _pad0: 0.0,
            };
            let uniform_buffer =
                self.device
                    .create_buffer_init(&wgpu::util::BufferInitDescriptor {
                        label: Some("default_material_buffer"),
                        contents: bytemuck::cast_slice(&[uniform]),
                        usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
                    });
            gpu_bytes += std::mem::size_of::<MaterialUniform>();
            let bind_group = self.device.create_bind_group(&wgpu::BindGroupDescriptor {
                label: Some("default_material_bind_group"),
                layout: &self.material_bind_group_layout,
                entries: &[wgpu::BindGroupEntry {
                    binding: 0,
                    resource: uniform_buffer.as_entire_binding(),
                }],
            });
            self.gpu_materials.push(GpuMaterial {
                uniform_buffer,
                bind_group,
            });
        }

        // 2. Upload meshes
        for mesh in &scene.meshes {
            let mut gpu_prims = Vec::new();
            for prim in &mesh.primitives {
                let vertex_bytes = prim.vertices.len() * std::mem::size_of::<Vertex>();
                let index_bytes = prim.indices.len() * std::mem::size_of::<u32>();

                let vertex_buffer =
                    self.device
                        .create_buffer_init(&wgpu::util::BufferInitDescriptor {
                            label: Some("primitive_vertex_buffer"),
                            contents: bytemuck::cast_slice(&prim.vertices),
                            usage: wgpu::BufferUsages::VERTEX,
                        });

                let index_buffer =
                    self.device
                        .create_buffer_init(&wgpu::util::BufferInitDescriptor {
                            label: Some("primitive_index_buffer"),
                            contents: bytemuck::cast_slice(&prim.indices),
                            usage: wgpu::BufferUsages::INDEX,
                        });

                gpu_bytes += vertex_bytes + index_bytes;

                gpu_prims.push(GpuPrimitive {
                    vertex_buffer,
                    index_buffer,
                    index_count: prim.indices.len() as u32,
                    material_index: prim.material_index.unwrap_or(0),
                });
            }
            self.gpu_meshes.push(GpuMesh {
                primitives: gpu_prims,
            });
        }

        // 3. Upload nodes
        for node in &scene.nodes {
            let n_mat = Scene::normal_matrix_for(&node.world_transform);
            let uniform = ObjectUniform {
                model: node.world_transform.to_cols_array(),
                normal_col0: [n_mat.x_axis.x, n_mat.x_axis.y, n_mat.x_axis.z, 0.0],
                normal_col1: [n_mat.y_axis.x, n_mat.y_axis.y, n_mat.y_axis.z, 0.0],
                normal_col2: [n_mat.z_axis.x, n_mat.z_axis.y, n_mat.z_axis.z, 0.0],
                is_selected: 0,
                _pad0: 0,
                _pad1: 0,
                _pad2: 0,
            };

            let object_buffer = self
                .device
                .create_buffer_init(&wgpu::util::BufferInitDescriptor {
                    label: Some("object_uniform_buffer"),
                    contents: bytemuck::cast_slice(&[uniform]),
                    usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
                });

            gpu_bytes += std::mem::size_of::<ObjectUniform>();

            let object_bind_group = self.device.create_bind_group(&wgpu::BindGroupDescriptor {
                label: Some("object_bind_group"),
                layout: &self.object_bind_group_layout,
                entries: &[wgpu::BindGroupEntry {
                    binding: 0,
                    resource: object_buffer.as_entire_binding(),
                }],
            });

            self.gpu_nodes.push(GpuNode {
                object_buffer,
                object_bind_group,
                mesh_index: node.mesh_index,
            });
        }

        // Camera uniform buffer and depth texture overhead
        gpu_bytes += std::mem::size_of::<CameraUniform>();
        gpu_bytes += (self.width as usize) * (self.height as usize) * 4;

        self.resident_gpu_bytes = gpu_bytes;
    }

    /// Uploads a synthetic colored cube for M01 gate validation
    pub fn create_synthetic_cube_scene(&mut self) -> Scene {
        let p = [
            [-0.5f32, -0.5, -0.5],
            [0.5, -0.5, -0.5],
            [0.5, 0.5, -0.5],
            [-0.5, 0.5, -0.5],
            [-0.5, -0.5, 0.5],
            [0.5, -0.5, 0.5],
            [0.5, 0.5, 0.5],
            [-0.5, 0.5, 0.5],
        ];

        let faces: [([usize; 4], [f32; 3], [f32; 4]); 6] = [
            ([0, 3, 2, 1], [0.0, 0.0, -1.0], [0.8, 0.2, 0.2, 1.0]), // Red
            ([4, 5, 6, 7], [0.0, 0.0, 1.0], [0.2, 0.8, 0.2, 1.0]),  // Green
            ([0, 1, 5, 4], [0.0, -1.0, 0.0], [0.2, 0.2, 0.8, 1.0]), // Blue
            ([3, 7, 6, 2], [0.0, 1.0, 0.0], [0.8, 0.8, 0.2, 1.0]),  // Yellow
            ([0, 4, 7, 3], [-1.0, 0.0, 0.0], [0.8, 0.2, 0.8, 1.0]), // Magenta
            ([1, 2, 6, 5], [1.0, 0.0, 0.0], [0.2, 0.8, 0.8, 1.0]),  // Cyan
        ];

        let mut vertices = Vec::new();
        let mut indices = Vec::new();

        for (indices_f, normal, _color) in &faces {
            let start = vertices.len() as u32;
            for &idx in indices_f {
                vertices.push(Vertex {
                    position: p[idx],
                    normal: *normal,
                });
            }
            indices.extend_from_slice(&[start, start + 1, start + 2, start, start + 2, start + 3]);
        }

        let prim = crate::scene::Primitive {
            vertices,
            indices,
            material_index: Some(0),
            bounds: crate::scene::AABB::new(glam::Vec3::splat(-0.5), glam::Vec3::splat(0.5)),
        };

        let mesh = crate::scene::Mesh {
            name: Some("synthetic_cube".into()),
            primitives: vec![prim],
        };

        let mat = Material {
            name: Some("synthetic_mat".into()),
            base_color: [0.35, 0.65, 0.85, 1.0],
            roughness: 0.3,
            metallic: 0.0,
            double_sided: true,
        };

        let node = crate::scene::Node {
            name: Some("synthetic_node".into()),
            anatomy_id: Some("synthetic:cube".into()),
            mesh_index: Some(0),
            local_transform: Mat4::IDENTITY,
            world_transform: Mat4::IDENTITY,
            children: Vec::new(),
            visible: true,
        };

        let mut scene = Scene {
            nodes: vec![node],
            meshes: vec![mesh],
            materials: vec![mat],
            root_nodes: vec![0],
            selected_id: None,
            bounds: crate::scene::AABB::new(glam::Vec3::splat(-0.5), glam::Vec3::splat(0.5)),
            revision: 1,
        };
        scene.update_world_transforms();
        self.upload_scene(&scene);
        scene
    }

    pub fn render(
        &mut self,
        target_view: &wgpu::TextureView,
        camera: &Camera,
        scene: &Scene,
    ) -> Result<(), String> {
        // 1. Update camera uniform
        let camera_uniform = CameraUniform {
            view_proj: camera.view_projection_matrix().to_cols_array(),
            camera_pos: camera.eye().to_array(),
            _pad0: 0.0,
        };
        self.queue.write_buffer(
            &self.camera_buffer,
            0,
            bytemuck::cast_slice(&[camera_uniform]),
        );

        // 2. Update object uniforms (selection status and transform)
        for (i, node) in scene.nodes.iter().enumerate() {
            if i >= self.gpu_nodes.len() {
                break;
            }
            let is_sel = if let (Some(sel), Some(aid)) = (&scene.selected_id, &node.anatomy_id) {
                if sel == aid { 1u32 } else { 0u32 }
            } else {
                0u32
            };

            let n_mat = Scene::normal_matrix_for(&node.world_transform);
            let obj_uniform = ObjectUniform {
                model: node.world_transform.to_cols_array(),
                normal_col0: [n_mat.x_axis.x, n_mat.x_axis.y, n_mat.x_axis.z, 0.0],
                normal_col1: [n_mat.y_axis.x, n_mat.y_axis.y, n_mat.y_axis.z, 0.0],
                normal_col2: [n_mat.z_axis.x, n_mat.z_axis.y, n_mat.z_axis.z, 0.0],
                is_selected: is_sel,
                _pad0: 0,
                _pad1: 0,
                _pad2: 0,
            };

            self.queue.write_buffer(
                &self.gpu_nodes[i].object_buffer,
                0,
                bytemuck::cast_slice(&[obj_uniform]),
            );
        }

        // 3. Command encoder and render pass
        let mut encoder = self
            .device
            .create_command_encoder(&wgpu::CommandEncoderDescriptor {
                label: Some("render_command_encoder"),
            });

        {
            let mut render_pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: Some("main_render_pass"),
                color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                    view: target_view,
                    resolve_target: None,
                    ops: wgpu::Operations {
                        load: wgpu::LoadOp::Clear(self.clear_color),
                        store: wgpu::StoreOp::Store,
                    },
                    depth_slice: None,
                })],
                depth_stencil_attachment: Some(wgpu::RenderPassDepthStencilAttachment {
                    view: &self.depth_texture_view,
                    depth_ops: Some(wgpu::Operations {
                        load: wgpu::LoadOp::Clear(1.0),
                        store: wgpu::StoreOp::Store,
                    }),
                    stencil_ops: None,
                }),
                timestamp_writes: None,
                occlusion_query_set: None,
                multiview_mask: None,
            });

            render_pass.set_pipeline(&self.pipeline);
            render_pass.set_bind_group(0, &self.camera_bind_group, &[]);

            for (node_idx, node) in scene.nodes.iter().enumerate() {
                if !node.visible {
                    continue;
                }
                let gpu_node = match self.gpu_nodes.get(node_idx) {
                    Some(gn) => gn,
                    None => continue,
                };
                let mesh_idx = match gpu_node.mesh_index {
                    Some(mi) => mi,
                    None => continue,
                };
                let gpu_mesh = match self.gpu_meshes.get(mesh_idx) {
                    Some(gm) => gm,
                    None => continue,
                };

                render_pass.set_bind_group(1, &gpu_node.object_bind_group, &[]);

                for prim in &gpu_mesh.primitives {
                    let mat_idx = prim
                        .material_index
                        .min(self.gpu_materials.len().saturating_sub(1));
                    if let Some(gpu_mat) = self.gpu_materials.get(mat_idx) {
                        render_pass.set_bind_group(2, &gpu_mat.bind_group, &[]);
                    }

                    render_pass.set_vertex_buffer(0, prim.vertex_buffer.slice(..));
                    render_pass
                        .set_index_buffer(prim.index_buffer.slice(..), wgpu::IndexFormat::Uint32);
                    render_pass.draw_indexed(0..prim.index_count, 0, 0..1);
                }
            }
        }

        self.queue.submit(std::iter::once(encoder.finish()));
        Ok(())
    }
}

impl Drop for Renderer {
    fn drop(&mut self) {
        self.destroy_gpu_resources();
        self.camera_buffer.destroy();
    }
}
