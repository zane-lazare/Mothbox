# GBIF Submission Guide

## Overview

This guide walks through the complete workflow for submitting Mothbox insect observation data to the Global Biodiversity Information Facility (GBIF). GBIF is the world's largest biodiversity data network, providing open access to occurrence records from around the globe.

**What you'll learn**:
- How to prepare Mothbox photos for GBIF submission
- How to export data in Darwin Core format
- How to validate your data before submission
- How to publish data to GBIF

## What is GBIF?

The [Global Biodiversity Information Facility](https://www.gbif.org) is an international network that provides free and open access to biodiversity data. Researchers, policymakers, and the public use GBIF data to understand species distributions, track changes over time, and support conservation decisions.

**Key terms**:
- **Occurrence record**: An observation of a species at a specific time and place
- **Darwin Core**: The international standard for biodiversity data (format Mothbox uses)
- **IPT**: Integrated Publishing Toolkit - GBIF's data publishing software

---

## Prerequisites

### Required

1. **GPS-enabled photos**: All photos must have GPS coordinates
   - Enable GPS module on Mothbox during capture
   - Or run GPS EXIF tagger on existing photos (see [GPS EXIF User Guide](GPS_EXIF_USER_GUIDE.md))

2. **GBIF account**: Free registration at [gbif.org](https://www.gbif.org/user/profile)

### Recommended

1. **Species identification**: Tag photos with species names in the Gallery
2. **Deployment metadata**: Add collection-level context (location name, project info)
3. **GPS accuracy data**: Include HDOP values for coordinate uncertainty

---

## Step 1: Prepare Your Data

### Verify GPS Data

All photos submitted to GBIF must have GPS coordinates. Photos without GPS are excluded from Darwin Core exports.

**Check GPS status**:

```bash
# Verify a single photo has GPS
python3 -m webui.cli.verify_gps_exif /var/lib/mothbox/photos/photo.jpg

# Check entire directory
python3 -m webui.cli.verify_gps_exif --directory /var/lib/mothbox/photos
```

**If photos lack GPS**:

```bash
# Run GPS EXIF tagger (uses current GPS from controls.txt)
python3 webui/cli/gps_exif_tagger.py --directory /var/lib/mothbox/photos

# Dry run first to preview changes
python3 webui/cli/gps_exif_tagger.py --directory /var/lib/mothbox/photos --dry-run
```

### Add Species Identification

While not strictly required, species identification significantly increases the value of your data.

**In the Gallery web UI**:
1. Navigate to Gallery page
2. Click on a photo to open lightbox
3. In the metadata panel, add species information:
   - **Species** (scientific name): e.g., "Actias luna"
   - **Common name**: e.g., "Luna Moth"
   - **Confidence level**: certain, probable, possible, or unknown

**Confidence levels map to Darwin Core qualifiers**:

| Mothbox Confidence | Darwin Core Qualifier | When to use |
|-------------------|----------------------|-------------|
| `certain` | *(empty)* | Confident, verified identification |
| `probable` | `cf.` | Likely correct, needs confirmation |
| `possible` | `aff.` | Related to, but uncertain species |
| `unknown` | `?` | Cannot identify, but want to record observation |

### Add Deployment Metadata (Optional)

Deployment metadata adds collection-level context to your export:

**In the Export web UI**:
1. Navigate to Export page
2. In Deployment section, click "Create New" or select existing
3. Fill in deployment information:
   - **Deployment name**: e.g., "Oak Ridge Forest Survey 2024"
   - **Location name**: e.g., "Oak Ridge, Tennessee, USA"
   - **Start/End dates**: Survey period
   - **Environmental conditions**: Habitat type, weather, etc.

This information is included in the exported Darwin Core CSV as additional context.

---

## Step 2: Export as Darwin Core

### Using the Web UI

1. **Navigate** to Export page in web UI
2. **Select** "Darwin Core" format card
3. **Choose preset** (optional): Select "GBIF Biodiversity Export"
   - This preset filters to photos with species identification
   - Enables validation and warnings
4. **Configure filters** (optional):
   - Date range: Select survey period
   - Deployment: Filter to specific collection
   - Has species: Toggle on for quality data
5. **Review preview**: Verify photo count and sample data
6. **Click** "Start Export"
7. **Wait** for job to complete (progress bar shows status)
8. **Download** the CSV file

### Using the CLI/API

**Export entire deployment**:

```bash
curl -X GET \
  'http://localhost:5000/api/export/darwin-core/deployment/2024/oak-ridge?validate=true' \
  -H 'Accept: text/csv' \
  -o mothbox_darwin_core.csv
```

**Export specific photos**:

```bash
curl -X POST 'http://localhost:5000/api/export/darwin-core/batch' \
  -H 'Content-Type: application/json' \
  -H 'Accept: text/csv' \
  -H 'X-CSRFToken: YOUR_TOKEN' \
  -d '{
    "photo_paths": ["photo1.jpg", "photo2.jpg"],
    "validate": true,
    "include_warnings": true
  }' \
  -o mothbox_darwin_core.csv
```

**Export using async job queue** (recommended for large exports):

```bash
# Create export job
curl -X POST 'http://localhost:5000/api/export/jobs' \
  -H 'Content-Type: application/json' \
  -H 'X-CSRFToken: YOUR_TOKEN' \
  -d '{
    "format": "darwin_core",
    "filter": {
      "deployment": "oak-ridge-2024",
      "has_species": true
    }
  }'

# Returns job_id, then poll for status:
curl 'http://localhost:5000/api/export/jobs/JOB_ID'

# Download when status is "completed":
curl -O 'http://localhost:5000/api/export/jobs/JOB_ID/download'
```

### Understanding the CSV Output

Your Darwin Core CSV will contain these columns:

| Column | Description | Example |
|--------|-------------|---------|
| `occurrenceID` | Unique record identifier | `mothbox:oak-ridge-2024:a1b2c3d4` |
| `basisOfRecord` | Record type | `MachineObservation` |
| `eventDate` | Observation date/time | `2024-06-15T22:30:00` |
| `decimalLatitude` | GPS latitude | `35.9606` |
| `decimalLongitude` | GPS longitude | `-83.9207` |
| `geodeticDatum` | Coordinate system | `WGS84` |
| `scientificName` | Species scientific name | `Actias luna` |
| `vernacularName` | Species common name | `Luna Moth` |
| `identificationQualifier` | Confidence qualifier | `cf.` |
| `coordinateUncertaintyInMeters` | GPS accuracy | `2.5` |
| `occurrenceStatus` | Presence/absence | `present` |
| `recordedBy` | Observer | `Mothbox` |
| `institutionCode` | Data provider | `Mothbox` |
| `collectionCode` | Deployment name | `oak-ridge-2024` |
| `catalogNumber` | Photo filename | `moth_2024_06_15.jpg` |
| `associatedMedia` | Photo path/URL | `/photos/moth_2024_06_15.jpg` |

---

## Step 3: Validate with GBIF Validator

Before submitting to GBIF, validate your CSV to catch issues early.

### Using GBIF Data Validator

1. **Go to**: [gbif.org/tools/data-validator](https://www.gbif.org/tools/data-validator)
2. **Upload** your Darwin Core CSV file
3. **Wait** for validation to complete
4. **Review** the validation report

### Understanding Validation Results

**Types of issues**:

| Icon | Severity | Action Required |
|------|----------|-----------------|
| Red | Error | Must fix before publishing |
| Yellow | Warning | Should fix for data quality |
| Blue | Info | Suggestions for improvement |

**Common validation errors**:

| Error | Cause | Solution |
|-------|-------|----------|
| "Missing coordinates" | GPS not embedded in photo | Run GPS EXIF tagger |
| "Invalid scientific name" | Typo in species name | Verify against [GBIF backbone](https://www.gbif.org/species/search) |
| "Date parsing error" | Invalid timestamp format | Check photo EXIF date |
| "Coordinate out of range" | GPS lat/lon beyond limits | Check GPS configuration |

### Fixing Validation Errors

If validation fails:

1. **Identify** the problematic photos from error details
2. **Fix** the issues in Mothbox:
   - Add missing GPS with GPS EXIF tagger
   - Correct species names in Gallery
   - Check timestamp format in metadata
3. **Re-export** with the same filters
4. **Re-validate** the new CSV

---

## Step 4: Publish to GBIF

There are two main ways to publish data to GBIF:

### Option A: IPT (Recommended for Institutions)

The Integrated Publishing Toolkit (IPT) is GBIF's preferred method for organizations that will publish data regularly.

**Requirements**:
- Your institution must be registered with GBIF
- Access to an IPT instance (your institution may host one, or use a shared IPT)
- Dataset metadata (title, description, contact info)

**Workflow**:

1. **Register** your organization with GBIF (if not already)
   - Contact your national GBIF node
   - Or register at [gbif.org/become-a-publisher](https://www.gbif.org/become-a-publisher)

2. **Access** your institution's IPT
   - Ask your IT admin for access
   - Or use a cloud-hosted IPT (e.g., [ipt.gbif.org](https://ipt.gbif.org) for testing)

3. **Create** a new Darwin Core Archive resource:
   - Click "Create a new resource"
   - Upload your Darwin Core CSV as "occurrence core"
   - Add metadata (title, abstract, citation, contact)

4. **Publish** the dataset:
   - Review preview
   - Register with GBIF
   - Receive DOI for your dataset

**Resources**:
- [IPT User Manual](https://ipt.gbif.org/manual/en/ipt/latest/)
- [GBIF Publisher Guide](https://www.gbif.org/publisher-guidance)

### Option B: Dataset Registration (Simplified)

For individuals or one-time submissions, you can work with GBIF or a node to publish data.

**Workflow**:

1. **Contact** your national GBIF node:
   - Find your node at [gbif.org/the-gbif-network](https://www.gbif.org/the-gbif-network)
   - Explain your dataset and request publishing assistance

2. **Prepare** dataset metadata:
   - Dataset title
   - Description
   - Contact information
   - License (recommend CC0 or CC-BY)

3. **Submit** your Darwin Core CSV:
   - Your node may publish on your behalf
   - Or they may guide you through their IPT

**Alternative**: Partner with a local university, museum, or research institution that already publishes to GBIF.

---

## Darwin Core Field Reference

### Required Fields

These fields must be present for GBIF to accept your data:

| Field | Mothbox Source | Description |
|-------|----------------|-------------|
| `occurrenceID` | Auto-generated | Unique identifier for each observation |
| `basisOfRecord` | `MachineObservation` | Indicates automated camera capture |
| `eventDate` | Photo timestamp | ISO 8601 date/time |
| `decimalLatitude` | GPS latitude | -90 to 90 degrees |
| `decimalLongitude` | GPS longitude | -180 to 180 degrees |
| `geodeticDatum` | `WGS84` | Coordinate reference system |

### Recommended Fields

These fields improve data quality and usability:

| Field | Mothbox Source | Description |
|-------|----------------|-------------|
| `scientificName` | Species tag | Scientific name of observed species |
| `vernacularName` | Common name tag | Common name in local language |
| `coordinateUncertaintyInMeters` | GPS HDOP | Accuracy of GPS coordinates |
| `identificationQualifier` | Confidence level | Qualifier like cf., aff., ? |
| `occurrenceStatus` | `present` | Indicates species was observed |

### Collection Fields

These fields provide context about the dataset:

| Field | Mothbox Source | Description |
|-------|----------------|-------------|
| `institutionCode` | `Mothbox` | Data provider identifier |
| `collectionCode` | Deployment name | Collection/survey identifier |
| `catalogNumber` | Photo filename | Individual record identifier |
| `associatedMedia` | Photo path | Link to photo file |

---

## Best Practices

### Data Quality

1. **GPS first**: Ensure GPS is working before starting survey
2. **Verify coordinates**: Spot-check that locations are correct on a map
3. **Consistent IDs**: Use established species naming (check GBIF backbone)
4. **Document uncertainty**: Use confidence levels honestly

### Metadata

1. **Descriptive names**: Use clear deployment names (location + year)
2. **Contact info**: Include email for data questions
3. **License**: Use CC0 or CC-BY for maximum reuse
4. **Methods**: Document survey methodology in dataset description

### Ongoing

1. **Regular exports**: Export and submit data regularly (monthly/quarterly)
2. **Version control**: Keep copies of submitted CSVs
3. **Updates**: Notify GBIF if you need to correct published data
4. **DOI citation**: Use GBIF-assigned DOI when citing your dataset

---

## Troubleshooting

### Photos Not Appearing in Export

**Problem**: Export has fewer photos than expected

**Solutions**:
1. Check GPS status: `python3 -m webui.cli.verify_gps_exif --directory /path`
2. Disable `validate=true` temporarily to see which photos are skipped
3. Check filter settings (date range, deployment, tags)

### "Darwin Core validation failed" Error

**Problem**: Export fails with validation error

**Cause**: Photos missing GPS coordinates or timestamp

**Solution**:
```bash
# Tag photos with GPS
python3 webui/cli/gps_exif_tagger.py --force

# Re-export
curl 'http://localhost:5000/api/export/darwin-core/deployment/your-deployment'
```

### Species Names Not Matching GBIF

**Problem**: GBIF validator shows unknown species names

**Solution**:
1. Search GBIF backbone: [gbif.org/species/search](https://www.gbif.org/species/search)
2. Use accepted scientific name (not synonyms)
3. Include authority if needed (e.g., "Actias luna (Linnaeus, 1758)")
4. Update species tags in Gallery and re-export

### Coordinate Issues

**Problem**: GBIF shows coordinates in wrong location

**Possible causes**:
1. GPS module not properly calibrated
2. Coordinates recorded when GPS had poor fix
3. Hemisphere/sign issues (negative for W and S)

**Solutions**:
1. Verify GPS fix quality (`gps_fix_mode=3` for 3D fix)
2. Check HDOP values (< 5 is good)
3. Compare coordinates with known location on map

---

## Resources

### GBIF Documentation

- [Darwin Core Quick Reference](https://dwc.tdwg.org/terms/)
- [GBIF Publishing Data](https://www.gbif.org/publishing-data)
- [IPT User Manual](https://ipt.gbif.org/manual/en/ipt/latest/)
- [Data Validator](https://www.gbif.org/tools/data-validator)
- [Species Backbone](https://www.gbif.org/species/search)

### Mothbox Documentation

- [Export User Guide](EXPORT_USER_GUIDE.md) - All export formats
- [GPS EXIF User Guide](GPS_EXIF_USER_GUIDE.md) - GPS tagging
- [Darwin Core API](dev/api/darwin-core-export.md) - Developer reference

### Support

- **GBIF Help Desk**: [gbif.org/contact-us](https://www.gbif.org/contact-us)
- **National Nodes**: [gbif.org/the-gbif-network](https://www.gbif.org/the-gbif-network)
- **Mothbox Issues**: GitHub issue tracker

---

## Version History

- **v1.0** (December 2024): Initial release
  - Darwin Core export workflow
  - GBIF validation guide
  - IPT publishing instructions
  - Field mapping reference
