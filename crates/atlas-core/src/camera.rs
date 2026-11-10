use glam::{Mat4, Vec3, Vec4};

#[derive(Debug, Clone, Copy)]
pub struct Ray {
    pub origin: Vec3,
    pub direction: Vec3,
}

impl Ray {
    pub fn new(origin: Vec3, direction: Vec3) -> Self {
        Self {
            origin,
            direction: direction.normalize(),
        }
    }

    pub fn point_at(&self, t: f32) -> Vec3 {
        self.origin + self.direction * t
    }
}

#[derive(Debug, Clone)]
pub struct Camera {
    pub target: Vec3,
    pub distance: f32,
    pub yaw: f32,   // azimuth in radians
    pub pitch: f32, // elevation in radians [-PI/2 + eps, PI/2 - eps]
    pub fovy: f32,  // in radians
    pub aspect: f32,
    pub znear: f32,
    pub zfar: f32,
}

impl Default for Camera {
    fn default() -> Self {
        Self {
            target: Vec3::new(0.0, 0.88, 0.0), // approximate center of pelvis
            distance: 0.8,                     // ~80cm distance
            yaw: 0.0,
            pitch: 0.15,
            fovy: std::f32::consts::FRAC_PI_4, // 45 degrees
            aspect: 1.0,
            znear: 0.01,
            zfar: 50.0,
        }
    }
}

impl Camera {
    pub fn eye(&self) -> Vec3 {
        let cos_p = self.pitch.cos();
        let sin_p = self.pitch.sin();
        let sin_y = self.yaw.sin();
        let cos_y = self.yaw.cos();

        // In our coordinate system: +Y up, +Z anterior, +X patient left
        let offset = Vec3::new(
            self.distance * cos_p * sin_y,
            self.distance * sin_p,
            self.distance * cos_p * cos_y,
        );
        self.target + offset
    }

    pub fn view_matrix(&self) -> Mat4 {
        Mat4::look_at_rh(self.eye(), self.target, Vec3::Y)
    }

    pub fn projection_matrix(&self) -> Mat4 {
        // glam Mat4::perspective_rh maps NDC Z to [0, 1] for Vulkan/WebGPU/Metal
        Mat4::perspective_rh(self.fovy, self.aspect, self.znear, self.zfar)
    }

    pub fn view_projection_matrix(&self) -> Mat4 {
        self.projection_matrix() * self.view_matrix()
    }

    pub fn orbit(&mut self, delta_x: f32, delta_y: f32) {
        let sensitivity = 0.005;
        self.yaw -= delta_x * sensitivity;
        self.pitch = (self.pitch + delta_y * sensitivity).clamp(
            -std::f32::consts::FRAC_PI_2 + 0.01,
            std::f32::consts::FRAC_PI_2 - 0.01,
        );
    }

    pub fn pan(&mut self, delta_x: f32, delta_y: f32) {
        let factor = self.distance * 0.0015;
        let forward = (self.target - self.eye()).normalize();
        let right = forward.cross(Vec3::Y).normalize();
        let up = right.cross(forward).normalize();

        self.target += right * (-delta_x * factor) + up * (delta_y * factor);
    }

    pub fn zoom(&mut self, delta: f32) {
        let zoom_factor = (delta * 0.0015).clamp(-0.8, 0.8);
        self.distance = (self.distance * (1.0 + zoom_factor)).clamp(0.05, 10.0);
    }

    pub fn fit_bounds(&mut self, min: Vec3, max: Vec3) {
        let center = (min + max) * 0.5;
        let extent = max - min;
        let radius = extent.length() * 0.5;

        self.target = center;
        // distance to fit bounding sphere within fovy and aspect
        let half_fov = self.fovy * 0.5;
        let min_fov = if self.aspect < 1.0 {
            2.0 * ((half_fov.tan() * self.aspect).atan())
        } else {
            self.fovy
        };
        let dist = radius / (min_fov * 0.5).sin();
        self.distance = (dist * 1.15).max(0.1);
    }

    pub fn set_preset(&mut self, preset_id: u32) {
        match preset_id {
            0 => {
                // Anterior-superior overview
                self.yaw = 0.0;
                self.pitch = 0.25;
            }
            1 => {
                // Lateral-oblique (45 deg yaw, 15 deg pitch)
                self.yaw = 0.785;
                self.pitch = 0.25;
            }
            2 => {
                // Perineal-inferior (low angle looking up)
                self.yaw = 0.0;
                self.pitch = -0.50;
            }
            _ => {}
        }
    }

    /// Screen coords (x, y) where x in [0, width], y in [0, height].
    /// Transforms into a world-space Ray.
    pub fn ray_from_screen(&self, x_css: f32, y_css: f32, width: f32, height: f32) -> Ray {
        // Normalized Device Coordinates (NDC):
        // x in [-1, 1], y in [-1, 1] (y is flipped: 0 is top, height is bottom)
        let ndc_x = (2.0 * x_css / width) - 1.0;
        let ndc_y = 1.0 - (2.0 * y_css / height);

        let inv_view_proj = self.view_projection_matrix().inverse();

        // Near plane point in NDC: z = 0.0 (wgpu depth range [0, 1])
        let near_clip = Vec4::new(ndc_x, ndc_y, 0.0, 1.0);
        let near_world = inv_view_proj * near_clip;
        let near_pt = near_world.truncate() / near_world.w;

        // Far plane point in NDC: z = 1.0
        let far_clip = Vec4::new(ndc_x, ndc_y, 1.0, 1.0);
        let far_world = inv_view_proj * far_clip;
        let far_pt = far_world.truncate() / far_world.w;

        Ray::new(near_pt, (far_pt - near_pt).normalize())
    }
}
