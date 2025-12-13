# iNaturalist Export API

## Overview

The Mothbox Photo Gallery supports exporting photos with XMP sidecar files for import into iNaturalist, a citizen science platform for sharing biodiversity observations. The export creates ZIP archives containing original photos paired with metadata-rich XMP files compatible with iNaturalist's import workflow.

**Related Issue:** [#118](https://github.com/zane-lazare/Mothbox/issues/118)

## iNaturalist Import Workflow

iNaturalist uses XMP sidecar files to read metadata during bulk photo imports. The workflow is:

1. Export photos from Mothbox as iNaturalist ZIP
2. Extract ZIP archive
3. Upload photos to iNaturalist (bulk uploader reads XMP files for metadata)
4. Review and publish observations

**Key Resources:**
- [iNaturalist Help: Bulk Upload](https://www.inaturalist.org/pages/help#bulk)
- [XMP Specification](https://www.adobe.com/devnet/xmp.html)

---

## API Endpoints

### Export Batch

**POST /api/export/inaturalist/batch**

Export multiple photos as iNaturalist-compatible ZIP archive.

**Rate Limit**: 5 requests per minute

#### Request Body

```json
{
    "photo_paths": ["photo1.jpg", "photo2.jpg", "subdir/photo3.jpg"],
    "options": {
        "include_xmp_sidecars": true,
        "include_manifest": true,
        "include_csv_summary": true,
        "flatten_structure": false
    }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| photo_paths | array | Yes | List of relative photo paths |
| options.include_xmp_sidecars | boolean | No | Include XMP files (default: true) |
| options.include_manifest | boolean | No | Include manifest.json (default: true) |
| options.include_csv_summary | boolean | No | Include summary.csv (default: true) |
| options.flatten_structure | boolean | No | Flatten directory structure (default: false) |

#### Response Format

Based on `Accept` header:

**`Accept: application/json` (default):**

```json
{
    "success": true,
    "zip_path": "/tmp/export_abc123.zip",
    "zip_size_bytes": 12500000,
    "photo_count": 50,
    "xmp_count": 50,
    "took_ms": 3500.5
}
```

**`Accept: application/zip`:**

Returns ZIP file download with `Content-Disposition` header:
```
Content-Disposition: attachment; filename="inaturalist_export_20240115_103000.zip"
```

#### Error Responses

| Code | Error | Cause |
|------|-------|-------|
| 400 | "Request must be JSON" | Missing Content-Type: application/json |
| 400 | "No photos specified" | Empty or missing photo_paths array |
| 400 | "All photo_paths must be non-empty strings" | Invalid path format |
| 400 | "Batch size exceeds maximum limit" | Too many photos (default max: 1000) |
| 403 | "Invalid path" | Path traversal attempt |
| 500 | "ZIP export failed" | Internal error during export |

---

### Export Deployment

**GET /api/export/inaturalist/deployment/{path}**

Export entire deployment directory as iNaturalist ZIP.

**Rate Limit**: 5 requests per minute

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | Yes | Deployment directory path (relative to PHOTOS_DIR) |

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| include_xmp | boolean | true | Include XMP sidecars |
| include_manifest | boolean | true | Include manifest.json |
| include_csv_summary | boolean | true | Include summary.csv |

#### Response Format

Same as batch export - based on `Accept` header.

#### Example

```bash
# JSON response with file path
curl -X GET \
  'http://localhost:5000/api/export/inaturalist/deployment/2024/oak-ridge' \
  -H 'Accept: application/json'

# Direct ZIP download
curl -X GET \
  'http://localhost:5000/api/export/inaturalist/deployment/2024/oak-ridge?include_xmp=true' \
  -H 'Accept: application/zip' \
  -o inaturalist_export.zip
```

---

### Preview Export

**POST /api/export/inaturalist/preview**

Preview export without creating ZIP (dry run).

**Rate Limit**: 5 requests per minute

#### Request Body

```json
{
    "photo_paths": ["photo1.jpg", "photo2.jpg"]
}
```

#### Response

```json
{
    "valid_photos": 45,
    "invalid_photos": 5,
    "estimated_zip_size_bytes": 125000000,
    "validation_results": [
        {
            "photo_path": "no_gps.jpg",
            "is_valid": false,
            "missing_fields": ["GPS coordinates"],
            "warnings": []
        }
    ],
    "sample_xmp": "<?xpacket begin='...' id='W5M0MpCehiHzreSzNTczkc9d'?>..."
}
```

---

## XMP Metadata Format

Photos are paired with XMP sidecar files containing metadata in multiple namespaces:

### Dublin Core (dc:)

| XMP Field | Mothbox Source | iNaturalist Import |
|-----------|---------------|-------------------|
| dc:title | species + species_common_name | Parsed for taxon |
| dc:description | notes + tags | Observation notes |
| dc:subject | tags + taxonomy hierarchy | Tags + taxonomy |
| dc:creator | "Mothbox" | Observer |
| dc:rights | "CC BY-NC 4.0" | License info |

### XMP Core (xmp:)

| XMP Field | Mothbox Source | Description |
|-----------|---------------|-------------|
| xmp:CreateDate | timestamp | Photo capture timestamp |
| xmp:ModifyDate | timestamp | Same as CreateDate |

### IPTC Extension (Iptc4xmpExt:)

| XMP Field | Mothbox Source | Description |
|-----------|---------------|-------------|
| Iptc4xmpExt:LocationShown | latitude, longitude | GPS coordinates |

### Photoshop (photoshop:)

| XMP Field | Mothbox Source | Description |
|-----------|---------------|-------------|
| photoshop:DateCreated | timestamp | ISO 8601 date |

---

## Taxonomy Keywords

Species are tagged with hierarchical keywords for improved discoverability:

```xml
<dc:subject>
  <rdf:Bag>
    <rdf:li>moth</rdf:li>
    <rdf:li>lepidoptera</rdf:li>
    <rdf:li>taxonomy:kingdom=Animalia</rdf:li>
    <rdf:li>taxonomy:phylum=Arthropoda</rdf:li>
    <rdf:li>taxonomy:class=Insecta</rdf:li>
    <rdf:li>taxonomy:order=Lepidoptera</rdf:li>
    <rdf:li>taxonomy:genus=Actias</rdf:li>
    <rdf:li>taxonomy:species=Actias luna</rdf:li>
  </rdf:Bag>
</dc:subject>
```

The taxonomy hierarchy is automatically generated when species name is present.

---

## ZIP Archive Structure

### Flat Structure (flatten_structure: true)

```
inaturalist_export.zip
├── photo1.jpg
├── photo1.xmp
├── photo2.jpg
├── photo2.xmp
├── manifest.json
└── summary.csv
```

### Preserved Structure (flatten_structure: false, default)

```
inaturalist_export.zip
├── 2024/
│   ├── oak-ridge/
│   │   ├── photo1.jpg
│   │   ├── photo1.xmp
│   │   ├── photo2.jpg
│   │   └── photo2.xmp
├── manifest.json
└── summary.csv
```

---

## Example XMP Sidecar

```xml
<?xpacket begin='﻿' id='W5M0MpCehiHzreSzNTczkc9d'?>
<x:xmpmeta xmlns:x='adobe:ns:meta/'>
  <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
    <rdf:Description rdf:about=''
        xmlns:dc='http://purl.org/dc/elements/1.1/'
        xmlns:xmp='http://ns.adobe.com/xap/1.0/'
        xmlns:photoshop='http://ns.adobe.com/photoshop/1.0/'
        xmlns:Iptc4xmpExt='http://iptc.org/std/Iptc4xmpExt/2008-02-29/'>

      <dc:title>
        <rdf:Alt>
          <rdf:li xml:lang='x-default'>Luna Moth (Actias luna)</rdf:li>
        </rdf:Alt>
      </dc:title>

      <dc:description>
        <rdf:Alt>
          <rdf:li xml:lang='x-default'>Beautiful specimen captured at night. Tags: moth, lepidoptera, night</rdf:li>
        </rdf:Alt>
      </dc:description>

      <dc:subject>
        <rdf:Bag>
          <rdf:li>moth</rdf:li>
          <rdf:li>lepidoptera</rdf:li>
          <rdf:li>night</rdf:li>
          <rdf:li>taxonomy:kingdom=Animalia</rdf:li>
          <rdf:li>taxonomy:phylum=Arthropoda</rdf:li>
          <rdf:li>taxonomy:class=Insecta</rdf:li>
          <rdf:li>taxonomy:order=Lepidoptera</rdf:li>
          <rdf:li>taxonomy:species=Actias luna</rdf:li>
        </rdf:Bag>
      </dc:subject>

      <dc:creator>
        <rdf:Seq>
          <rdf:li>Mothbox</rdf:li>
        </rdf:Seq>
      </dc:creator>

      <dc:rights>
        <rdf:Alt>
          <rdf:li xml:lang='x-default'>CC BY-NC 4.0</rdf:li>
        </rdf:Alt>
      </dc:rights>

      <xmp:CreateDate>2024-01-15T10:30:00</xmp:CreateDate>
      <xmp:ModifyDate>2024-01-15T10:30:00</xmp:ModifyDate>

      <photoshop:DateCreated>2024-01-15</photoshop:DateCreated>

      <Iptc4xmpExt:LocationShown>
        <rdf:Bag>
          <rdf:li rdf:parseType='Resource'>
            <Iptc4xmpExt:City>San Francisco</Iptc4xmpExt:City>
            <Iptc4xmpExt:ProvinceState>CA</Iptc4xmpExt:ProvinceState>
            <Iptc4xmpExt:CountryName>USA</Iptc4xmpExt:CountryName>
            <Iptc4xmpExt:GPSLatitude>37.7749</Iptc4xmpExt:GPSLatitude>
            <Iptc4xmpExt:GPSLongitude>-122.4194</Iptc4xmpExt:GPSLongitude>
          </rdf:li>
        </rdf:Bag>
      </Iptc4xmpExt:LocationShown>

    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>
<?xpacket end='w'?>
```

---

## Performance

| Operation | Target | Typical |
|-----------|--------|---------|
| Single XMP generation | <10ms | ~5ms |
| 50 photos ZIP | <5 seconds | ~3.5s |
| 100 photos ZIP | <10 seconds | ~7s |
| Throughput | >10 photos/sec | ~15 photos/sec |

---

## Code Examples

### Python

```python
import requests

# Batch export (JSON response)
response = requests.post(
    'http://localhost:5000/api/export/inaturalist/batch',
    json={
        'photo_paths': ['photo1.jpg', 'photo2.jpg'],
        'options': {
            'include_xmp_sidecars': True,
            'include_manifest': True
        }
    }
)
data = response.json()
print(f"Exported {data['photo_count']} photos to {data['zip_path']}")

# Batch export (ZIP download)
response = requests.post(
    'http://localhost:5000/api/export/inaturalist/batch',
    json={'photo_paths': ['photo1.jpg', 'photo2.jpg']},
    headers={'Accept': 'application/zip'}
)
with open('inaturalist_export.zip', 'wb') as f:
    f.write(response.content)

# Deployment export
response = requests.get(
    'http://localhost:5000/api/export/inaturalist/deployment/2024/oak-ridge',
    headers={'Accept': 'application/zip'}
)
with open('deployment_export.zip', 'wb') as f:
    f.write(response.content)

# Preview export
response = requests.post(
    'http://localhost:5000/api/export/inaturalist/preview',
    json={'photo_paths': ['photo1.jpg', 'photo2.jpg']}
)
preview = response.json()
print(f"Valid photos: {preview['valid_photos']}")
print(f"Estimated size: {preview['estimated_zip_size_bytes'] / (1024*1024):.1f} MB")
```

### JavaScript

```javascript
// Batch export (JSON)
const response = await fetch('/api/export/inaturalist/batch', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  },
  body: JSON.stringify({
    photo_paths: ['photo1.jpg', 'photo2.jpg'],
    options: {
      include_xmp_sidecars: true,
      include_manifest: true
    }
  })
});
const data = await response.json();
console.log(`Exported ${data.photo_count} photos`);

// Batch export (ZIP download)
const response = await fetch('/api/export/inaturalist/batch', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/zip'
  },
  body: JSON.stringify({
    photo_paths: ['photo1.jpg', 'photo2.jpg']
  })
});
const blob = await response.blob();
const url = window.URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = 'inaturalist_export.zip';
a.click();
```

---

## iNaturalist Upload Guide

### Step 1: Export from Mothbox

Choose photos to export and create iNaturalist ZIP:

```bash
curl -X POST \
  'http://localhost:5000/api/export/inaturalist/batch' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/zip' \
  -d '{"photo_paths": ["photo1.jpg", "photo2.jpg"]}' \
  -o inaturalist_export.zip
```

### Step 2: Extract ZIP

```bash
unzip inaturalist_export.zip -d inaturalist_photos
```

### Step 3: Upload to iNaturalist

1. Log in to iNaturalist
2. Navigate to "Upload" → "Bulk Upload"
3. Select photos from extracted directory
4. iNaturalist reads XMP sidecars automatically
5. Review pre-filled metadata (species, location, date)
6. Publish observations

### Best Practices

- **GPS Required**: iNaturalist requires GPS coordinates. Ensure Mothbox GPS is enabled.
- **Species Identification**: Review species names before upload. Use `species_confidence` to indicate uncertainty.
- **Tags**: Use descriptive tags for better discoverability.
- **License**: Default CC BY-NC 4.0 license is compatible with iNaturalist's license options.

---

## Validation

Photos are validated before export. Warnings are included for:

- Missing GPS coordinates (iNaturalist requires location)
- Missing species identification
- Missing timestamp

Use the preview endpoint to check validation before exporting:

```bash
curl -X POST \
  'http://localhost:5000/api/export/inaturalist/preview' \
  -H 'Content-Type: application/json' \
  -d '{"photo_paths": ["photo1.jpg", "photo2.jpg"]}' \
  | jq '.validation_results'
```

---

## Related Documentation

- [Export Metadata Service](../services/export-metadata-service.md)
- [Sidecar Metadata Schema](../schemas/sidecar-metadata.md)
- [Deployment Metadata Schema](../schemas/deployment-metadata.md)
- [Darwin Core Export API](./darwin-core-export.md)
