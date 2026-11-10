/**
 * ANATOM.IA — CANONICAL TA2 PELVIS CATALOG (M05-A.1)
 * Verified against TA2.csv and catalog.json. Categories and systems
 * mapped via explicit TA2 dictionary (NO heuristic substring matching).
 */
import type { AnatomyStructure } from "../runtime/bridge-types";

export const PELVIS_STRUCTURES: AnatomyStructure[] = [
  {
    "id": "ta2:1071",
    "ta2Id": "1071",
    "system": "Sistema esquelético",
    "labels": {
      "es": "Hueso sacro",
      "en": "Sacrum",
      "la": "Os sacrum"
    },
    "side": "unpaired_or_unspecified",
    "category": "bone",
    "visible": true
  },
  {
    "id": "ta2:1092",
    "ta2Id": "1092",
    "system": "Sistema esquelético",
    "labels": {
      "es": "Cóccix",
      "en": "Coccyx",
      "la": "Os coccygis"
    },
    "side": "unpaired_or_unspecified",
    "category": "bone",
    "visible": true
  },
  {
    "id": "ta2:1855",
    "ta2Id": "1855",
    "system": "Articulaciones de la pelvis",
    "labels": {
      "es": "Sínfisis púbica",
      "en": "Pubic symphysis",
      "la": "Symphysis pubica"
    },
    "side": "unpaired_or_unspecified",
    "category": "joint",
    "visible": true
  },
  {
    "id": "ta2:3401",
    "ta2Id": "3401",
    "system": "Sistema urinario",
    "labels": {
      "es": "Vejiga urinaria",
      "en": "Urinary bladder",
      "la": "Vesica urinaria"
    },
    "side": "unpaired_or_unspecified",
    "category": "organ",
    "visible": true
  },
  {
    "id": "ta2:3637",
    "ta2Id": "3637",
    "system": "Sistema genital masculino",
    "labels": {
      "es": "Próstata",
      "en": "Prostate",
      "la": "Prostata"
    },
    "side": "unpaired_or_unspecified",
    "category": "organ",
    "visible": true
  },
  {
    "id": "ta2:3631:left",
    "ta2Id": "3631",
    "system": "Sistema genital masculino",
    "labels": {
      "es": "Glándula seminal",
      "en": "Seminal gland",
      "la": "Glandula seminalis"
    },
    "side": "left",
    "category": "organ",
    "visible": true
  },
  {
    "id": "ta2:3631:right",
    "ta2Id": "3631",
    "system": "Sistema genital masculino",
    "labels": {
      "es": "Glándula seminal",
      "en": "Seminal gland",
      "la": "Glandula seminalis"
    },
    "side": "right",
    "category": "organ",
    "visible": true
  },
  {
    "id": "ta2:3576:left",
    "ta2Id": "3576",
    "system": "Sistema genital masculino",
    "labels": {
      "es": "Testículo",
      "en": "Testis",
      "la": "Testis"
    },
    "side": "left",
    "category": "organ",
    "visible": true
  },
  {
    "id": "ta2:3576:right",
    "ta2Id": "3576",
    "system": "Sistema genital masculino",
    "labels": {
      "es": "Testículo",
      "en": "Testis",
      "la": "Testis"
    },
    "side": "right",
    "category": "organ",
    "visible": true
  },
  {
    "id": "ta2:3668",
    "ta2Id": "3668",
    "system": "Sistema genital masculino",
    "labels": {
      "es": "Glande del pene",
      "en": "Glans penis",
      "la": "Glans penis"
    },
    "side": "unpaired_or_unspecified",
    "category": "organ",
    "visible": true
  },
  {
    "id": "ta2:3678",
    "ta2Id": "3678",
    "system": "Sistema genital masculino",
    "labels": {
      "es": "Cuerpo cavernoso del pene",
      "en": "Corpus cavernosum of penis",
      "la": "Corpus cavernosum penis"
    },
    "side": "unpaired_or_unspecified",
    "category": "organ",
    "visible": true
  },
  {
    "id": "ta2:3681",
    "ta2Id": "3681",
    "system": "Sistema genital masculino",
    "labels": {
      "es": "Cuerpo esponjoso del pene",
      "en": "Corpus spongiosum of penis",
      "la": "Corpus spongiosum penis"
    },
    "side": "unpaired_or_unspecified",
    "category": "organ",
    "visible": true
  },
  {
    "id": "ta2:1852:left",
    "ta2Id": "1852",
    "system": "Articulaciones de la pelvis",
    "labels": {
      "es": "Ligamento sacroespinoso",
      "en": "Sacrospinous ligament",
      "la": "Ligamentum sacrospinale"
    },
    "side": "left",
    "category": "joint",
    "visible": true
  },
  {
    "id": "ta2:1852:right",
    "ta2Id": "1852",
    "system": "Articulaciones de la pelvis",
    "labels": {
      "es": "Ligamento sacroespinoso",
      "en": "Sacrospinous ligament",
      "la": "Ligamentum sacrospinale"
    },
    "side": "right",
    "category": "joint",
    "visible": true
  },
  {
    "id": "ta2:1850:left",
    "ta2Id": "1850",
    "system": "Articulaciones de la pelvis",
    "labels": {
      "es": "Ligamento sacrotuberoso",
      "en": "Sacrotuberous ligament",
      "la": "Ligamentum sacrotuberale"
    },
    "side": "left",
    "category": "joint",
    "visible": true
  },
  {
    "id": "ta2:1850:right",
    "ta2Id": "1850",
    "system": "Articulaciones de la pelvis",
    "labels": {
      "es": "Ligamento sacrotuberoso",
      "en": "Sacrotuberous ligament",
      "la": "Ligamentum sacrotuberale"
    },
    "side": "right",
    "category": "joint",
    "visible": true
  },
  {
    "id": "ta2:2412:left",
    "ta2Id": "2412",
    "system": "Músculos de la pelvis",
    "labels": {
      "es": "Músculo coccígeo",
      "en": "Coccygeus muscle",
      "la": "Musculus coccygeus"
    },
    "side": "left",
    "category": "muscle",
    "visible": true
  },
  {
    "id": "ta2:2412:right",
    "ta2Id": "2412",
    "system": "Músculos de la pelvis",
    "labels": {
      "es": "Músculo coccígeo",
      "en": "Coccygeus muscle",
      "la": "Musculus coccygeus"
    },
    "side": "right",
    "category": "muscle",
    "visible": true
  },
  {
    "id": "ta2:4301:left",
    "ta2Id": "4301",
    "system": "Sistema cardiovascular",
    "labels": {
      "es": "Arteria ilíaca común",
      "en": "Common iliac artery",
      "la": "Arteria iliaca communis"
    },
    "side": "left",
    "category": "vascular",
    "visible": true
  },
  {
    "id": "ta2:4301:right",
    "ta2Id": "4301",
    "system": "Sistema cardiovascular",
    "labels": {
      "es": "Arteria ilíaca común",
      "en": "Common iliac artery",
      "la": "Arteria iliaca communis"
    },
    "side": "right",
    "category": "vascular",
    "visible": true
  },
  {
    "id": "ta2:4302:left",
    "ta2Id": "4302",
    "system": "Sistema cardiovascular",
    "labels": {
      "es": "Arteria ilíaca interna",
      "en": "Internal iliac artery",
      "la": "Arteria iliaca interna"
    },
    "side": "left",
    "category": "vascular",
    "visible": true
  },
  {
    "id": "ta2:4302:right",
    "ta2Id": "4302",
    "system": "Sistema cardiovascular",
    "labels": {
      "es": "Arteria ilíaca interna",
      "en": "Internal iliac artery",
      "la": "Arteria iliaca interna"
    },
    "side": "right",
    "category": "vascular",
    "visible": true
  },
  {
    "id": "ta2:5050:left",
    "ta2Id": "5050",
    "system": "Sistema cardiovascular",
    "labels": {
      "es": "Vena iliaca externa",
      "en": "External iliac vein",
      "la": "Vena iliaca externa"
    },
    "side": "left",
    "category": "vascular",
    "visible": true
  },
  {
    "id": "ta2:5050:right",
    "ta2Id": "5050",
    "system": "Sistema cardiovascular",
    "labels": {
      "es": "Vena iliaca externa",
      "en": "External iliac vein",
      "la": "Vena iliaca externa"
    },
    "side": "right",
    "category": "vascular",
    "visible": true
  },
  {
    "id": "ta2:6522:left",
    "ta2Id": "6522",
    "system": "Sistema nervioso periférico",
    "labels": {
      "es": "Nervio femoral",
      "en": "Femoral nerve",
      "la": "Nervus femoralis"
    },
    "side": "left",
    "category": "nervous",
    "visible": true
  },
  {
    "id": "ta2:6522:right",
    "ta2Id": "6522",
    "system": "Sistema nervioso periférico",
    "labels": {
      "es": "Nervio femoral",
      "en": "Femoral nerve",
      "la": "Nervus femoralis"
    },
    "side": "right",
    "category": "nervous",
    "visible": true
  }
];
