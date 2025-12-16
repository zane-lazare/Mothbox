# Export System - User Guide

## Overview

The Mothbox Export System enables researchers to export photo metadata in multiple formats for biodiversity databases, citizen science platforms, and custom analysis workflows. This guide covers the web UI workflow, export formats, and troubleshooting.

## Features

- **Multiple Export Formats**: Darwin Core (GBIF), iNaturalist, JSON, CSV
- **Async Job Queue**: Background processing for large exports (500+ photos)
- **Built-in Presets**: 6 pre-configured export templates for common workflows
- **Flexible Filtering**: Date range, deployment, tags, species, series type
- **Deployment Metadata**: Optional collection-level context for exports
- **Progress Tracking**: Real-time status updates during export
- **Auto-Cleanup**: Completed exports expire after 1 hour

## Prerequisites

### Hardware Requirements
- Mothbox with photos captured
- GPS module (recommended for GBIF/iNaturalist exports)

### Software Requirements
- Mothbox Web UI running (backend + frontend)
- Photos directory accessible

### Optional for Best Results
- GPS EXIF tagging enabled (see GPS_EXIF_USER_GUIDE.md)
- Species identification tags on photos
- Deployment metadata configured

---

## Quick Start

### 5-Step Export Workflow

1. **Navigate** to Export page in web UI
2. **Select** export format (Darwin Core, iNaturalist, JSON, or CSV)
3. **Configure** filters (date range, deployment, tags)
4. **Click** "Start Export" button
5. **Download** completed export file

**Typical export time**: 100 photos in ~10-30 seconds, 1000 photos in ~1-5 minutes

---

## Export Formats

Mothbox supports four export formats optimized for different use cases:

### Darwin Core CSV

**Best for**: GBIF submission, iDigBio, biodiversity databases

Darwin Core is the international standard for biodiversity data exchange. Mothbox generates occurrence records following the Darwin Core specification.

| Feature | Value |
|---------|-------|
| Output | Single CSV file |
| File size | ~1KB per 10 photos |
| GPS required | Yes (coordinates required for occurrence records) |
| Species required | Recommended (for meaningful biodiversity data) |
| Validation | GBIF-compatible field mapping |

**Use cases**:
- Submitting moth observations to GBIF
- Contributing to biodiversity portals
- Scientific data archiving

**Related documentation**: [GBIF Submission Guide](GBIF_SUBMISSION_GUIDE.md)

---

### iNaturalist Export

**Best for**: Bulk upload to iNaturalist, XMP metadata embedding

Creates a ZIP archive with photos and XMP sidecar files that iNaturalist can read automatically during upload.

| Feature | Value |
|---------|-------|
| Output | ZIP archive with photos + XMP files |
| File size | Large (includes photo copies) |
| GPS required | Required by iNaturalist |
| Species required | Recommended (auto-fills species field) |
| XMP metadata | Tags, species, notes, timestamps |

**Use cases**:
- Bulk uploading observations to iNaturalist
- Sharing observations with citizen science community
- Coordinated BioBlitz data submission

---

### JSON Export

**Best for**: Programmatic access, custom analysis, data pipelines

Exports metadata in structured JSON format with nested fields for flexible data processing.

| Feature | Value |
|---------|-------|
| Output | Single JSON file |
| File size | ~500 bytes per photo |
| GPS required | No |
| Species required | No |
| Fields | All available metadata |

**Use cases**:
- Custom data analysis scripts
- Integration with external tools
- Data backup and archiving
- Machine learning pipelines

---

### CSV Export

**Best for**: Spreadsheet analysis, Excel import, tabular data

Exports flattened metadata in comma-separated format, compatible with all spreadsheet applications.

| Feature | Value |
|---------|-------|
| Output | Single CSV file |
| File size | ~200 bytes per photo |
| GPS required | No |
| Species required | No |
| Excel compatible | Yes (UTF-8 BOM option) |

**Use cases**:
- Excel/Google Sheets analysis
- Quick data review
- Sharing with collaborators
- Statistical analysis

---

### Format Comparison Table

| Feature | Darwin Core | iNaturalist | JSON | CSV |
|---------|-------------|-------------|------|-----|
| **Output type** | CSV | ZIP | JSON | CSV |
| **File size** | Small | Large | Medium | Small |
| **GPS required** | Yes | Yes | No | No |
| **Species recommended** | Yes | Yes | No | No |
| **Photos included** | No | Yes (optional) | No | No |
| **Best for** | GBIF | iNaturalist | Analysis | Spreadsheets |
| **Processing speed** | Fast | Slower | Fast | Fast |

---

## Built-in Presets

Mothbox includes 6 pre-configured presets for common workflows:

### 1. GBIF Biodiversity Export
- **Format**: Darwin Core CSV
- **Filter**: Only photos with species identification
- **Options**: Validation enabled, warnings included
- **Use case**: Submitting quality biodiversity data to GBIF

### 2. iNaturalist Upload Package
- **Format**: iNaturalist ZIP
- **Filter**: None (all photos)
- **Options**: XMP sidecars, manifest, CSV summary
- **Use case**: Bulk uploading observations to iNaturalist

### 3. Simple JSON Export
- **Format**: JSON
- **Filter**: None (all photos)
- **Options**: Default
- **Use case**: General metadata export for analysis

### 4. Simple CSV Export
- **Format**: CSV
- **Filter**: None (all photos)
- **Options**: UTF-8 BOM for Excel compatibility
- **Use case**: Spreadsheet-friendly metadata export

### 5. HDR Series Export
- **Format**: JSON
- **Filter**: HDR series photos only
- **Options**: Default
- **Use case**: Exporting bracketed exposure sequences

### 6. Focus Bracket Series Export
- **Format**: JSON
- **Filter**: Focus bracket photos only
- **Options**: Default
- **Use case**: Exporting focus stacking sequences

---

## Web UI Walkthrough

### Export Page Layout

The Export page is divided into two main areas:

**Left Panel (Configuration)**
- Format selector cards (4 formats in 2x2 grid)
- Preset dropdown menu
- Filter panel (collapsible sections)
- Deployment selector and editor
- Format-specific options
- Export button with photo count

**Right Panel (Preview)**
- Live preview of export output
- Photo count matching current filters
- Sample data in selected format
- Updates in real-time as options change

### Step-by-Step: Creating an Export

#### Step 1: Select Export Format

At the top of the configuration panel, you'll see four format cards arranged in a 2x2 grid:

- **Darwin Core**: Green border, globe icon - For GBIF/biodiversity databases
- **iNaturalist**: Orange border, leaf icon - For iNaturalist bulk upload
- **JSON**: Blue border, code brackets icon - For programmatic access
- **CSV**: Gray border, table icon - For spreadsheet analysis

Click a card to select that format. The selected card displays a blue highlight border. The preview panel updates to show sample output in that format.

#### Step 2: Choose a Preset (Optional)

Below the format cards, a dropdown menu shows available presets:

- **"Select a preset..."** (default, no preset)
- **GBIF Biodiversity Export**
- **iNaturalist Upload Package**
- **Simple JSON Export**
- **Simple CSV Export**
- **HDR Series Export**
- **Focus Bracket Series Export**

Selecting a preset auto-fills the format, filters, and options. You can then modify any setting to customize the export.

#### Step 3: Configure Filters

The filter panel contains collapsible sections:

**Date Range**
- Start date picker (YYYY-MM-DD)
- End date picker (YYYY-MM-DD)
- Clear buttons to reset each field

**Deployment**
- Dropdown to select existing deployment directory
- Only photos within selected deployment are included

**Tags**
- Multi-select tag input
- Type to search available tags
- Click to add/remove tags
- Photos must have at least one selected tag (ANY mode)

**Series Type**
- Dropdown: None, HDR, Focus Bracket
- Filters to specific photo series types

**Has Species**
- Toggle switch
- When enabled, only includes photos with species identification

#### Step 4: Add Deployment Metadata (Optional)

Below the filter panel, the Deployment section allows adding collection-level context:

**Deployment Selector**
- Dropdown to select existing deployment
- "Create New" option for new deployments
- "None" option to export without deployment metadata

**Deployment Editor** (expanded when editing)
- Deployment name (required)
- Location name (optional)
- Latitude/Longitude (optional, decimal degrees)
- Altitude (optional, meters)
- Start/End dates (optional)
- Environmental conditions (optional, JSON)
- Custom fields (optional)
- "Auto-fill from Photos" button - populates fields from selected photos' GPS/timestamps

The "Auto-fill from Photos" feature analyzes your filtered photos and suggests:
- Centroid coordinates from GPS data
- Date range from photo timestamps
- Altitude from GPS altitude

You can review and adjust auto-filled values before saving.

#### Step 5: Configure Format Options

Options vary by selected format:

**Darwin Core Options**
- `validate`: Enable GBIF validation (default: true)
- `include_warnings`: Include validation warnings in output (default: true)

**iNaturalist Options**
- `include_xmp_sidecars`: Generate XMP metadata files (default: true)
- `include_manifest`: Include JSON manifest file (default: true)
- `include_csv_summary`: Include CSV summary spreadsheet (default: true)
- `include_photos`: Bundle photo copies in ZIP (default: varies)

**JSON Options**
- `pretty_print`: Format JSON with indentation (default: false)
- `include_raw_exif`: Include raw EXIF data (default: false)

**CSV Options**
- `include_bom`: Add UTF-8 BOM for Excel (default: true)
- `delimiter`: Field separator (comma, tab, semicolon)

#### Step 6: Preview Export

The right panel shows a live preview:

- **Photo count**: "X photos match current filters"
- **Sample output**: First few records in selected format
- **Format indicator**: Shows which format is selected
- **Updates live**: Changes as you modify filters/options

Review the preview to verify:
- Correct number of photos selected
- Expected fields appear in output
- Data looks correct

#### Step 7: Start Export

At the bottom of the configuration panel:

- **"Start Export" button**: Shows photo count (e.g., "Export 150 Photos")
- **Disabled states**:
  - No format selected: "Select a format"
  - No photos match: "No photos match filters"
  - Export in progress: "Export running..."

Click the button to create an export job. The job enters the queue and begins processing.

#### Step 8: Monitor Progress

After starting, a progress panel appears:

- **Job ID**: Unique identifier for the export
- **Status**: pending → running → completed (or failed)
- **Progress bar**: Visual percentage complete
- **Phase indicator**: Current operation (Initializing, Collecting, Exporting, Finalizing)
- **Cancel button**: Stop the export (available while pending/running)

**Progress phases**:
1. **Initializing**: Setting up export job
2. **Collecting**: Gathering photos matching filters
3. **Exporting**: Processing photos and generating output
4. **Finalizing**: Writing output file, cleanup

#### Step 9: Download Result

When status changes to "completed":

- **"Download" button** appears (replaces progress bar)
- **File info**: Shows output file size
- **Expiration notice**: "Available for 1 hour"

Click "Download" to save the export file to your computer.

**After download**:
- Completed exports remain visible for 1 hour
- After 1 hour, the output file is automatically deleted
- Job history shows past exports for reference

### Managing Export Jobs

**Job List Panel** (below the export form)

Displays all export jobs with:
- Job ID (shortened UUID)
- Format icon
- Status badge (color-coded)
- Created timestamp
- Photo count
- Actions: Download (if completed), Cancel (if running), Delete

**Status Colors**:
- Gray: pending
- Blue: running
- Green: completed
- Red: failed
- Yellow: cancelled
- Dim: expired

---

## Filter Options Reference

### Date Range Filter

| Field | Format | Example | Description |
|-------|--------|---------|-------------|
| `date_start` | ISO 8601 | `2024-01-01` | Include photos from this date |
| `date_end` | ISO 8601 | `2024-12-31` | Include photos until this date |

Photos are filtered by their capture timestamp (from EXIF or filename).

### Deployment Filter

| Field | Type | Description |
|-------|------|-------------|
| `deployment` | string | Deployment directory path (relative to photos root) |

Only photos within the specified deployment directory are included.

### Tags Filter

| Field | Type | Description |
|-------|------|-------------|
| `tags` | array | List of tag strings to match |

Photos must have at least one of the specified tags (OR logic).

### Series Type Filter

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `series_type` | string | `hdr`, `focus_bracket` | Filter by photo series type |

Filters to photos that are part of HDR or focus bracket sequences.

### Has Species Filter

| Field | Type | Description |
|-------|------|-------------|
| `has_species` | boolean | Only include photos with species identification |

When enabled, excludes photos without species tags.

### Explicit Photo Paths

| Field | Type | Description |
|-------|------|-------------|
| `photo_paths` | array | Explicit list of photo paths to export |

When provided, exports only the specified photos (ignores other filters).

---

## Performance Expectations

### Export Times

| Photo Count | Darwin Core | iNaturalist (metadata only) | iNaturalist (with photos) | JSON/CSV |
|-------------|-------------|----------------------------|---------------------------|----------|
| 100 | ~10 sec | ~15 sec | ~30 sec | ~5 sec |
| 500 | ~30 sec | ~60 sec | ~2 min | ~15 sec |
| 1,000 | ~60 sec | ~2 min | ~5 min | ~30 sec |
| 5,000 | ~3 min | ~8 min | ~20 min | ~2 min |

Times vary based on:
- Raspberry Pi model (Pi 5 faster than Pi 4)
- SD card speed
- Photo file sizes
- Network latency (if accessing remotely)

### Resource Usage

- **Memory**: ~50-100 MB per export job
- **CPU**: Single job at a time (protects Pi resources)
- **Disk**: Output files stored in `/tmp/exports/`
- **Timeout**: 10 minutes maximum per job

### Concurrent Jobs

The export system processes one job at a time to protect Raspberry Pi resources. Additional jobs are queued and processed in order (FIFO).

**Queue behavior**:
- Maximum 50 jobs in history
- Jobs older than 1 hour auto-expire
- Expired job files are automatically deleted

---

## Troubleshooting

### Common Errors

#### "No photos match filters"

**Cause**: Filter criteria too restrictive

**Solutions**:
1. Widen date range (or remove date filter)
2. Select different deployment (or clear deployment filter)
3. Disable "has_species" toggle if not all photos are identified
4. Clear tag filters if too specific
5. Verify photos exist in the selected directory

#### "Export failed: Disk full"

**Cause**: Insufficient storage for export output

**Solutions**:
1. Free up disk space on Raspberry Pi
2. Reduce number of photos in export (use filters)
3. Delete old export files: `rm /tmp/exports/export_*.{csv,zip,json}`
4. Check available space: `df -h /tmp`

#### "Rate limit exceeded"

**Cause**: Too many export requests in short time

**Solutions**:
1. Wait 60 seconds before trying again
2. Combine multiple exports into single larger export
3. Use CLI/API for batch operations

#### "Job timed out"

**Cause**: Export took longer than 10 minutes

**Solutions**:
1. Reduce photo count (use stricter filters)
2. For iNaturalist, disable photo bundling (`include_photos: false`)
3. Split into multiple smaller exports
4. Export during low-activity periods

#### "Darwin Core validation failed"

**Cause**: Missing required data for GBIF compliance

**Solutions**:
1. Ensure GPS EXIF is enabled (required for coordinates)
2. Run GPS EXIF tagger on photos: `python3 webui/cli/gps_exif_tagger.py`
3. Add species identification to photos
4. Use `validate: false` option to export without validation (not recommended for GBIF submission)

#### "Download button not appearing"

**Cause**: Job still processing or failed

**Solutions**:
1. Check job status - wait for "completed" status
2. If "failed", check error message in job details
3. Refresh the page if status appears stuck
4. Check backend logs: `journalctl -u mothbox-webui -f`

### Job Status Reference

| Status | Description | User Actions |
|--------|-------------|--------------|
| `pending` | Queued, waiting to start | Cancel available |
| `running` | Export in progress | Cancel available |
| `completed` | Ready for download | Download within 1 hour |
| `failed` | Error occurred | Check error, retry with different options |
| `cancelled` | User cancelled | Start new export |
| `expired` | Download TTL passed | Start new export |

### Error Messages Reference

| Error | HTTP Code | Meaning |
|-------|-----------|---------|
| "Invalid format" | 400 | Unrecognized export format name |
| "Invalid date format" | 400 | Date not in YYYY-MM-DD format |
| "Invalid preset" | 400 | Preset name doesn't exist |
| "Rate limit exceeded" | 429 | Too many requests, wait 60 seconds |
| "CSRF validation failed" | 403 | Token expired, refresh page |
| "Job not found" | 404 | Invalid or expired job ID |
| "Service unavailable" | 503 | Export service not running |

---

## iNaturalist Import Guide

This section provides step-by-step instructions for uploading Mothbox photos to iNaturalist.

### Prerequisites

- iNaturalist account (free at [inaturalist.org](https://www.inaturalist.org))
- Photos with GPS coordinates (required by iNaturalist)
- Species identification (recommended)

### Step 1: Export from Mothbox

**Using Web UI**:
1. Navigate to Export page
2. Select "iNaturalist Export" format
3. Use "iNaturalist Upload Package" preset (recommended)
4. Configure filters (optional)
5. Enable options:
   - **Include XMP sidecars**: Yes (auto-fills metadata during upload)
   - **Include manifest**: Yes (helps track uploaded photos)
   - **Include CSV summary**: Yes (spreadsheet overview)
6. Click "Start Export"
7. Download the ZIP file when complete

**Using CLI**:
```bash
curl -X POST 'http://localhost:5000/api/export/jobs' \
  -H 'Content-Type: application/json' \
  -H 'X-CSRFToken: YOUR_TOKEN' \
  -d '{
    "preset": "inaturalist_upload",
    "filter": {"deployment": "forest_2024"}
  }'
```

### Step 2: Extract the ZIP Archive

**Linux/macOS**:
```bash
unzip inaturalist_export.zip -d inaturalist_photos
```

**Windows**:
Right-click the ZIP file → Extract All → Choose destination

### ZIP Archive Structure

```
inaturalist_export.zip
├── 2024/
│   └── forest_survey/
│       ├── photo001.jpg
│       ├── photo001.xmp       ← XMP sidecar with metadata
│       ├── photo002.jpg
│       └── photo002.xmp
├── manifest.json              ← Photo list with metadata
└── summary.csv                ← Spreadsheet overview
```

### Step 3: Upload to iNaturalist

1. **Log in** to [iNaturalist.org](https://www.inaturalist.org)
2. **Click "Upload"** in the main navigation menu
3. **Drag photos** or click to select from extracted folder
4. **Wait for processing** - iNaturalist reads XMP files automatically
5. **Review pre-filled fields**:
   - Location: From GPS coordinates
   - Date/time: From photo timestamp
   - Species: From identification tags
   - Description: From notes field
6. **Make corrections** if needed
7. **Click "Submit"** to publish observations

### XMP Metadata Reference

The XMP sidecar files contain:

| XMP Field | Mothbox Source | iNaturalist Field |
|-----------|----------------|-------------------|
| `dc:title` | Species name | Taxon suggestion |
| `dc:description` | Notes + tags | Description |
| `dc:subject` | Tags + taxonomy | Tags |
| `xmp:CreateDate` | Timestamp | Observation date |
| `Iptc4xmpExt:GPSLatitude` | Latitude | Location |
| `Iptc4xmpExt:GPSLongitude` | Longitude | Location |

### Example XMP Sidecar

```xml
<?xpacket begin='' id='W5M0MpCehiHzreSzNTczkc9d'?>
<x:xmpmeta xmlns:x='adobe:ns:meta/'>
  <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
    <rdf:Description rdf:about=''
        xmlns:dc='http://purl.org/dc/elements/1.1/'
        xmlns:xmp='http://ns.adobe.com/xap/1.0/'
        xmlns:Iptc4xmpExt='http://iptc.org/std/Iptc4xmpExt/2008-02-29/'>

      <dc:title>
        <rdf:Alt>
          <rdf:li xml:lang='x-default'>Luna Moth (Actias luna)</rdf:li>
        </rdf:Alt>
      </dc:title>

      <dc:subject>
        <rdf:Bag>
          <rdf:li>moth</rdf:li>
          <rdf:li>saturniidae</rdf:li>
          <rdf:li>taxonomy:species=Actias luna</rdf:li>
        </rdf:Bag>
      </dc:subject>

      <xmp:CreateDate>2024-06-15T22:30:00</xmp:CreateDate>

      <Iptc4xmpExt:LocationShown>
        <rdf:Bag>
          <rdf:li rdf:parseType='Resource'>
            <Iptc4xmpExt:GPSLatitude>35.9606</Iptc4xmpExt:GPSLatitude>
            <Iptc4xmpExt:GPSLongitude>-83.9207</Iptc4xmpExt:GPSLongitude>
          </rdf:li>
        </rdf:Bag>
      </Iptc4xmpExt:LocationShown>

    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>
<?xpacket end='w'?>
```

### Troubleshooting iNaturalist Upload

#### Photos Not Showing Metadata

**Problem**: Location or species not auto-filling during upload

**Solutions**:
1. Ensure XMP files are in same directory as photos
2. Verify XMP filename matches photo filename (photo.xmp for photo.jpg)
3. Upload fewer photos at once (50-100 max)
4. Try uploading via drag-and-drop instead of file picker

#### Location Not Appearing

**Problem**: GPS coordinates not detected

**Cause**: Missing GPS data or invalid format

**Solutions**:
1. Verify photos have GPS EXIF: `python3 -m webui.cli.verify_gps_exif photo.jpg`
2. Re-export with GPS-tagged photos only (use `has_species` filter with GPS check)
3. Manually add location in iNaturalist if GPS unavailable

#### Species Suggestions Incorrect

**Problem**: iNaturalist suggesting wrong species

**Note**: XMP provides hints, but iNaturalist uses its own computer vision

**Solutions**:
1. Manually correct species after upload
2. Verify species names match iNaturalist taxonomy
3. Use iNaturalist's species search to confirm names

---

## Format Specifications

Detailed output format specifications for each export type.

### Darwin Core CSV Format

Darwin Core follows the [TDWG standard](https://dwc.tdwg.org/terms/) for biodiversity data.

**Example Output**:
```csv
occurrenceID,basisOfRecord,eventDate,decimalLatitude,decimalLongitude,geodeticDatum,scientificName,vernacularName,identificationQualifier,coordinateUncertaintyInMeters,occurrenceStatus,recordedBy,institutionCode,collectionCode,catalogNumber,associatedMedia
mothbox:oak-ridge-2024:a1b2c3d4,MachineObservation,2024-06-15T22:30:00,35.9606,-83.9207,WGS84,Actias luna,Luna Moth,,2.5,present,Mothbox,Mothbox,oak-ridge-2024,moth_2024_06_15.jpg,/photos/oak-ridge-2024/moth_2024_06_15.jpg
mothbox:oak-ridge-2024:e5f6g7h8,MachineObservation,2024-06-15T22:45:00,35.9610,-83.9210,WGS84,Automeris io,Io Moth,cf.,3.1,present,Mothbox,Mothbox,oak-ridge-2024,moth_2024_06_15_001.jpg,/photos/oak-ridge-2024/moth_2024_06_15_001.jpg
```

**Field Descriptions**:

| Field | Description | Example |
|-------|-------------|---------|
| `occurrenceID` | Unique record identifier | `mothbox:oak-ridge-2024:a1b2c3d4` |
| `basisOfRecord` | Type of observation | `MachineObservation` |
| `eventDate` | ISO 8601 timestamp | `2024-06-15T22:30:00` |
| `decimalLatitude` | GPS latitude (-90 to 90) | `35.9606` |
| `decimalLongitude` | GPS longitude (-180 to 180) | `-83.9207` |
| `geodeticDatum` | Coordinate system | `WGS84` |
| `scientificName` | Species scientific name | `Actias luna` |
| `vernacularName` | Common name | `Luna Moth` |
| `identificationQualifier` | Uncertainty qualifier | `cf.`, `aff.`, `?` |
| `coordinateUncertaintyInMeters` | GPS accuracy | `2.5` |
| `occurrenceStatus` | Presence indicator | `present` |
| `recordedBy` | Observer | `Mothbox` |
| `institutionCode` | Data provider | `Mothbox` |
| `collectionCode` | Deployment name | `oak-ridge-2024` |
| `catalogNumber` | Photo filename | `moth_2024_06_15.jpg` |
| `associatedMedia` | Photo path/URL | `/photos/oak-ridge-2024/moth_2024_06_15.jpg` |

### JSON Export Format

Nested structure preserving metadata hierarchy.

**Example Output**:
```json
{
  "filename": "moth_2024_06_15.jpg",
  "photo_path": "oak-ridge-2024/moth_2024_06_15.jpg",
  "capture": {
    "timestamp": "2024-06-15T22:30:00",
    "camera": {
      "make": "Arducam",
      "model": "OwlSight 64MP"
    },
    "settings": {
      "iso": 800,
      "aperture": 2.8,
      "shutter_speed": "1/60"
    }
  },
  "location": {
    "latitude": 35.9606,
    "longitude": -83.9207,
    "altitude": 350.5,
    "gps_accuracy": 2.5
  },
  "identification": {
    "species": "Actias luna",
    "common_name": "Luna Moth",
    "confidence": "certain",
    "tags": ["moth", "saturniidae", "green"]
  },
  "notes": "Large specimen, wings intact",
  "deployment": {
    "name": "Oak Ridge Survey 2024",
    "mothbox_id": "mothbox-001"
  },
  "series": {
    "type": "hdr",
    "index": 0,
    "total": 3
  }
}
```

**Field Reference**:

| Field Path | Type | Description |
|------------|------|-------------|
| `filename` | string | Photo filename |
| `photo_path` | string | Relative path from photos root |
| `capture.timestamp` | string | ISO 8601 capture time |
| `capture.camera.make` | string | Camera manufacturer |
| `capture.camera.model` | string | Camera model |
| `capture.settings.iso` | integer | ISO sensitivity |
| `capture.settings.aperture` | number | F-stop value |
| `capture.settings.shutter_speed` | string | Exposure time |
| `location.latitude` | number | GPS latitude |
| `location.longitude` | number | GPS longitude |
| `location.altitude` | number | GPS altitude (meters) |
| `location.gps_accuracy` | number | GPS HDOP |
| `identification.species` | string | Scientific name |
| `identification.common_name` | string | Common name |
| `identification.confidence` | string | certain/probable/possible/unknown |
| `identification.tags` | array | User tags |
| `notes` | string | User notes |
| `deployment.name` | string | Deployment name |
| `deployment.mothbox_id` | string | Device identifier |
| `series.type` | string | hdr/focus_bracket/null |
| `series.index` | integer | Position in series |
| `series.total` | integer | Total in series |

### CSV Export Format

Flat structure for spreadsheet compatibility.

**Example Output**:
```csv
filename,photo_path,timestamp,latitude,longitude,altitude,gps_accuracy,species,common_name,tags,notes,deployment_name,mothbox_id,series_type,series_index
moth_2024_06_15.jpg,oak-ridge-2024/moth_2024_06_15.jpg,2024-06-15T22:30:00,35.9606,-83.9207,350.5,2.5,Actias luna,Luna Moth,"moth,saturniidae,green",Large specimen,Oak Ridge Survey 2024,mothbox-001,hdr,0
moth_2024_06_15_001.jpg,oak-ridge-2024/moth_2024_06_15_001.jpg,2024-06-15T22:45:00,35.9610,-83.9210,352.0,3.1,Automeris io,Io Moth,"moth,saturniidae,yellow",,Oak Ridge Survey 2024,mothbox-001,,
```

**Column Reference**:

| Column | Type | Description |
|--------|------|-------------|
| `filename` | string | Photo filename |
| `photo_path` | string | Relative path |
| `timestamp` | string | ISO 8601 capture time |
| `latitude` | number | GPS latitude |
| `longitude` | number | GPS longitude |
| `altitude` | number | GPS altitude (meters) |
| `gps_accuracy` | number | GPS HDOP |
| `species` | string | Scientific name |
| `common_name` | string | Common name |
| `tags` | string | Comma-separated tags |
| `notes` | string | User notes |
| `deployment_name` | string | Deployment name |
| `mothbox_id` | string | Device identifier |
| `series_type` | string | hdr/focus_bracket or empty |
| `series_index` | integer | Position in series or empty |

### iNaturalist ZIP Format

Archive structure with photos and XMP sidecars.

**Archive Contents**:
```
inaturalist_export_20241215_143000.zip
├── oak-ridge-2024/
│   ├── moth_2024_06_15.jpg
│   ├── moth_2024_06_15.xmp
│   ├── moth_2024_06_15_001.jpg
│   └── moth_2024_06_15_001.xmp
├── manifest.json
└── summary.csv
```

**manifest.json**:
```json
{
  "export_date": "2024-12-15T14:30:00",
  "photo_count": 50,
  "xmp_count": 50,
  "photos": [
    {
      "filename": "moth_2024_06_15.jpg",
      "path": "oak-ridge-2024/moth_2024_06_15.jpg",
      "xmp_path": "oak-ridge-2024/moth_2024_06_15.xmp",
      "species": "Actias luna",
      "latitude": 35.9606,
      "longitude": -83.9207
    }
  ]
}
```

---

## Best Practices

### For GBIF Submissions

1. **Ensure GPS data**: All photos must have GPS coordinates
2. **Add species IDs**: Use the Gallery to tag photos with species
3. **Use validation**: Keep `validate: true` option enabled
4. **Review warnings**: Check validation warnings before submitting
5. **Test with sample**: Export 10 photos first, validate with GBIF validator

### For iNaturalist Uploads

1. **GPS required**: iNaturalist requires location for all observations
2. **Include XMP**: Enable `include_xmp_sidecars` for auto-fill during upload
3. **Review species**: Verify species IDs before export
4. **Batch size**: iNaturalist upload works best with <500 photos at a time

### For Data Analysis

1. **Use JSON for complex data**: Nested structure preserves relationships
2. **Use CSV for spreadsheets**: Flat structure works in Excel/Sheets
3. **Include all fields**: Don't filter unless specific fields needed
4. **Document your exports**: Note filter criteria used

### For Large Exports

1. **Schedule off-peak**: Run large exports when not actively using Mothbox
2. **Use filters**: Reduce photo count when possible
3. **Split exports**: Divide by date range or deployment
4. **Monitor progress**: Check job status periodically

---

## API Access

For programmatic exports, see the developer documentation:

- [Export Jobs API](dev/api/export-jobs.md) - Job queue endpoints
- [Export Presets API](dev/api/export-presets.md) - Preset management
- [Darwin Core Export API](dev/api/darwin-core-export.md) - GBIF format details
- [iNaturalist Export API](dev/api/inaturalist-export.md) - XMP format details
- [Generic Export API](dev/api/generic-export.md) - JSON/CSV details

### Quick API Examples

```bash
# Create Darwin Core export
curl -X POST "http://mothbox.local:5000/api/export/jobs" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_TOKEN" \
  -d '{"format": "darwin_core", "filter": {"deployment": "forest_2024"}}'

# Check job status
curl "http://mothbox.local:5000/api/export/jobs/JOB_ID"

# Download completed export
curl -O "http://mothbox.local:5000/api/export/jobs/JOB_ID/download"
```

---

## Related Documentation

- [GBIF Submission Guide](GBIF_SUBMISSION_GUIDE.md) - Complete GBIF workflow
- [GPS EXIF User Guide](GPS_EXIF_USER_GUIDE.md) - GPS tagging for exports
- [Deployment Sidecar Guide](DEPLOYMENT_SIDECAR.md) - Deployment metadata
- [Export API Index](dev/api/EXPORT_INDEX.md) - Developer API reference

---

## Version History

- **v1.0** (December 2024): Initial release
  - 4 export formats (Darwin Core, iNaturalist, JSON, CSV)
  - 6 built-in presets
  - Async job queue with SQLite persistence
  - Deployment metadata integration (Issue #200)
  - Photo aggregation for auto-fill (Issue #200)
  - Comprehensive test coverage (95%+)
