use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::types::{EngineError, ErrorCode, RegionId, VariantId};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CoordinateSystem {
    pub unit: String,
    pub up: String,
    pub anterior: String,
    pub patient_left: String,
}

impl Default for CoordinateSystem {
    fn default() -> Self {
        Self {
            unit: "meter".into(),
            up: "+Y".into(),
            anterior: "+Z".into(),
            patient_left: "+X".into(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CatalogRef {
    pub url: String,
    pub sha256: String,
    pub bytes: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RegionDef {
    pub id: String,
    pub packages: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PackageDef {
    pub id: String,
    pub variant: String,
    pub region: String,
    pub system: String,
    pub lod: u32,
    pub url: String,
    pub bytes: u64,
    pub sha256: String,
    pub encoding: String,
    pub required_extensions: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ManifestSnapshot {
    pub schema_version: u32,
    pub atlas_version: String,
    pub coordinate_system: CoordinateSystem,
    pub variants: Vec<String>,
    pub regions: Vec<RegionDef>,
    pub catalog: CatalogRef,
    pub packages: Vec<PackageDef>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RegionLoadPlan {
    pub region_id: RegionId,
    pub variant_id: VariantId,
    pub package_id: String,
    pub package_url: String,
    pub expected_package_sha256: String,
    pub expected_package_bytes: u64,
    pub lod: u32,
    pub catalog_url: String,
    pub expected_catalog_sha256: String,
    pub expected_catalog_bytes: u64,
}

pub fn is_safe_relative_url(url: &str) -> bool {
    if url.is_empty() || url.len() > 1000 {
        return false;
    }
    // Cannot start with '/' or '\'
    if url.starts_with('/') || url.starts_with('\\') {
        return false;
    }
    // Cannot contain '..' (path traversal)
    if url.contains("..") {
        return false;
    }
    // Cannot contain backslashes
    if url.contains('\\') {
        return false;
    }
    // Cannot contain ':' (prevents scheme injection like 'data:', 'javascript:', 'http:', or Windows drive 'C:')
    if url.contains(':') {
        return false;
    }
    // Characters must be strictly alphanumeric or '_', '.', '/', '-'
    url.chars()
        .all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '.' || c == '/' || c == '-')
}

pub fn is_valid_sha256_hex(hash: &str) -> bool {
    hash.len() == 64
        && hash
            .chars()
            .all(|c| c.is_ascii_digit() || ('a'..='f').contains(&c))
}

pub fn verify_sha256(expected_hex: &str, bytes: &[u8]) -> Result<(), EngineError> {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    let actual_hex = format!("{:x}", hasher.finalize());

    if actual_hex.eq_ignore_ascii_case(expected_hex) {
        Ok(())
    } else {
        Err(EngineError::new(
            ErrorCode::AssetCorrupt,
            format!(
                "SHA-256 digest mismatch: expected {}, calculated {}",
                expected_hex, actual_hex
            ),
            true,
        ))
    }
}

pub fn verify_size(expected_bytes: u64, actual_bytes: usize) -> Result<(), EngineError> {
    if expected_bytes == actual_bytes as u64 {
        Ok(())
    } else {
        Err(EngineError::new(
            ErrorCode::AssetCorrupt,
            format!(
                "Size mismatch: expected {} bytes, received {} bytes",
                expected_bytes, actual_bytes
            ),
            true,
        ))
    }
}

impl ManifestSnapshot {
    pub fn parse_json(json_str: &str) -> Result<Self, EngineError> {
        let snapshot: ManifestSnapshot = serde_json::from_str(json_str).map_err(|e| {
            EngineError::new(
                ErrorCode::AssetCorrupt,
                format!("Error deserializando manifest.json: {}", e),
                false,
            )
        })?;

        snapshot.validate()?;
        Ok(snapshot)
    }

    pub fn validate(&self) -> Result<(), EngineError> {
        if self.schema_version != 1 {
            return Err(EngineError::new(
                ErrorCode::AssetUnsupportedExtension,
                format!(
                    "schemaVersion {} no soportada (se requiere 1)",
                    self.schema_version
                ),
                false,
            ));
        }

        if self.coordinate_system.unit != "meter"
            || self.coordinate_system.up != "+Y"
            || self.coordinate_system.anterior != "+Z"
            || self.coordinate_system.patient_left != "+X"
        {
            return Err(EngineError::new(
                ErrorCode::InvalidCoordinates,
                format!(
                    "Sistema de coordenadas no canónico: {:?}",
                    self.coordinate_system
                ),
                false,
            ));
        }

        if !is_safe_relative_url(&self.catalog.url) {
            return Err(EngineError::new(
                ErrorCode::AssetCorrupt,
                format!(
                    "URL de catálogo sospechosa o insegura: '{}'",
                    self.catalog.url
                ),
                false,
            ));
        }

        if !is_valid_sha256_hex(&self.catalog.sha256) {
            return Err(EngineError::new(
                ErrorCode::AssetCorrupt,
                format!(
                    "Hash SHA-256 de catálogo inválido: '{}'",
                    self.catalog.sha256
                ),
                false,
            ));
        }

        if self.variants.is_empty() {
            return Err(EngineError::new(
                ErrorCode::AssetCorrupt,
                "Manifest no declara variantes anatómicas",
                false,
            ));
        }

        if self.regions.is_empty() {
            return Err(EngineError::new(
                ErrorCode::AssetCorrupt,
                "Manifest no declara regiones anatómicas",
                false,
            ));
        }

        if self.packages.is_empty() {
            return Err(EngineError::new(
                ErrorCode::AssetCorrupt,
                "Manifest no declara paquetes de geometría",
                false,
            ));
        }

        // Validate package definitions and URLs
        let mut package_ids = std::collections::HashSet::new();
        for pkg in &self.packages {
            if !package_ids.insert(&pkg.id) {
                return Err(EngineError::new(
                    ErrorCode::AssetCorrupt,
                    format!("ID de paquete duplicado en manifest: '{}'", pkg.id),
                    false,
                ));
            }

            if !is_safe_relative_url(&pkg.url) {
                return Err(EngineError::new(
                    ErrorCode::AssetCorrupt,
                    format!("URL de paquete sospechosa o insegura: '{}'", pkg.url),
                    false,
                ));
            }

            if !is_valid_sha256_hex(&pkg.sha256) {
                return Err(EngineError::new(
                    ErrorCode::AssetCorrupt,
                    format!("Hash SHA-256 de paquete inválido: '{}'", pkg.sha256),
                    false,
                ));
            }
        }

        // Validate referential integrity in regions
        for region in &self.regions {
            for pkg_id in &region.packages {
                if !package_ids.contains(pkg_id) {
                    return Err(EngineError::new(
                        ErrorCode::AssetCorrupt,
                        format!(
                            "Región '{}' referencia paquete inexistente: '{}'",
                            region.id, pkg_id
                        ),
                        false,
                    ));
                }
            }
        }

        Ok(())
    }

    pub fn select_package(
        &self,
        region_id: &str,
        variant_id: &str,
        preferred_lod: Option<u32>,
    ) -> Result<&PackageDef, EngineError> {
        // Enforce published anatomical boundaries (only 'pelvis' and 'male-adult')
        if region_id != "pelvis" {
            return Err(EngineError::new(
                ErrorCode::RegionUnavailable,
                format!("Región '{}' no está publicada en este atlas", region_id),
                false,
            ));
        }

        if variant_id != "male-adult" {
            return Err(EngineError::new(
                ErrorCode::RegionUnavailable,
                format!("Variante '{}' no está publicada en este atlas", variant_id),
                false,
            ));
        }

        // Filter packages for this region and variant
        let candidates: Vec<&PackageDef> = self
            .packages
            .iter()
            .filter(|p| p.region == region_id && p.variant == variant_id)
            .collect();

        if candidates.is_empty() {
            return Err(EngineError::new(
                ErrorCode::AssetNotFound,
                format!(
                    "No se encontraron paquetes para región '{}' y variante '{}'",
                    region_id, variant_id
                ),
                false,
            ));
        }

        // Check if only meshopt/unsupported packages exist
        let compatible_candidates: Vec<&PackageDef> = candidates
            .iter()
            .copied()
            .filter(|p| p.encoding == "none" && p.required_extensions.is_empty())
            .collect();

        if compatible_candidates.is_empty() {
            return Err(EngineError::new(
                ErrorCode::AssetUnsupportedExtension,
                "Paquete incompatible: el runtime actual no incluye decodificador WebAssembly para EXT_meshopt_compression o extensiones propietarias requeridas".to_string(),
                false,
            ));
        }

        // Selection based on preferred LOD
        if let Some(matched) = preferred_lod
            .and_then(|target_lod| compatible_candidates.iter().find(|p| p.lod == target_lod))
        {
            return Ok(matched);
        }

        // Default to lowest LOD number available (highest detail, e.g. LOD 0)
        let mut sorted = compatible_candidates;
        sorted.sort_by_key(|p| p.lod);
        Ok(sorted[0])
    }

    /// Reject any supplied plan that differs from the canonical, validated
    /// manifest snapshot. The browser transport must not be an authority on
    /// anatomical variants, package IDs, digests or paths.
    pub fn validate_load_plan(&self, plan: &RegionLoadPlan) -> Result<(), EngineError> {
        let expected = self.create_load_plan(&plan.region_id, &plan.variant_id, Some(plan.lod))?;
        if expected != *plan {
            return Err(EngineError::new(
                ErrorCode::AssetCorrupt,
                "Plan de carga inconsistente con el manifest validado",
                false,
            ));
        }
        Ok(())
    }

    pub fn create_load_plan(
        &self,
        region_id: &str,
        variant_id: &str,
        preferred_lod: Option<u32>,
    ) -> Result<RegionLoadPlan, EngineError> {
        let pkg = self.select_package(region_id, variant_id, preferred_lod)?;

        Ok(RegionLoadPlan {
            region_id: region_id.to_string(),
            variant_id: variant_id.to_string(),
            package_id: pkg.id.clone(),
            package_url: pkg.url.clone(),
            expected_package_sha256: pkg.sha256.clone(),
            expected_package_bytes: pkg.bytes,
            lod: pkg.lod,
            catalog_url: self.catalog.url.clone(),
            expected_catalog_sha256: self.catalog.sha256.clone(),
            expected_catalog_bytes: self.catalog.bytes,
        })
    }
}
