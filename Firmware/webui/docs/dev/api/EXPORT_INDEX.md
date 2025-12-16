# Export System Documentation Index

Quick reference for all export system documentation.

## User Documentation

| Document | Description |
|----------|-------------|
| [Export User Guide](../../EXPORT_USER_GUIDE.md) | Complete user guide for all export features |
| [GBIF Submission Guide](../../GBIF_SUBMISSION_GUIDE.md) | Darwin Core to GBIF workflow |
| [GPS EXIF User Guide](../../GPS_EXIF_USER_GUIDE.md) | GPS tagging for export compatibility |
| [Deployment Sidecar Guide](../../DEPLOYMENT_SIDECAR.md) | Deployment metadata for exports |

## Developer API Documentation

| Document | Description |
|----------|-------------|
| [Export Jobs API](./export-jobs.md) | Async job queue endpoints |
| [Export Presets API](./export-presets.md) | Preset management endpoints |
| [Darwin Core Export API](./darwin-core-export.md) | GBIF format details |
| [iNaturalist Export API](./inaturalist-export.md) | XMP/ZIP format details |
| [Generic Export API](./generic-export.md) | JSON/CSV format details |

---

## Quick Reference

### Export Formats

| Format | API Value | Output | Documentation |
|--------|-----------|--------|---------------|
| Darwin Core | `darwin_core` | CSV | [darwin-core-export.md](./darwin-core-export.md) |
| iNaturalist | `inaturalist` | ZIP | [inaturalist-export.md](./inaturalist-export.md) |
| JSON | `json` | JSON | [generic-export.md](./generic-export.md) |
| CSV | `csv` | CSV | [generic-export.md](./generic-export.md) |

### Built-in Presets

| Preset Name | Format | Filter | Use Case |
|-------------|--------|--------|----------|
| `gbif_biodiversity` | darwin_core | has_species: true | GBIF submission |
| `inaturalist_upload` | inaturalist | none | iNaturalist upload |
| `simple_json` | json | none | General metadata export |
| `simple_csv` | csv | none | Spreadsheet export |
| `hdr_series` | json | series_type: hdr | HDR photo series |
| `focus_bracket_series` | json | series_type: focus_bracket | Focus bracket series |

### API Endpoints Summary

#### Export Jobs (Async Queue)

```
POST   /api/export/jobs                  Create export job
GET    /api/export/jobs                  List jobs
GET    /api/export/jobs/<id>             Get job status
GET    /api/export/jobs/<id>/download    Download output
DELETE /api/export/jobs/<id>             Delete job
POST   /api/export/jobs/<id>/cancel      Cancel job
```

#### Export Presets

```
GET    /api/export/presets               List presets
GET    /api/export/presets/<name>        Get preset
POST   /api/export/presets               Create preset
DELETE /api/export/presets/<name>        Delete preset
```

#### Direct Export Endpoints

```
GET    /api/export/metadata/<path>       Single photo metadata
POST   /api/export/metadata/batch        Batch metadata
POST   /api/export/darwin-core/batch     Darwin Core CSV
GET    /api/export/darwin-core/deployment/<path>
POST   /api/export/inaturalist/batch     iNaturalist ZIP
GET    /api/export/inaturalist/deployment/<path>
POST   /api/export/json/batch            JSON export
GET    /api/export/json/deployment/<path>
POST   /api/export/csv/batch             CSV export
GET    /api/export/csv/deployment/<path>
POST   /api/export/aggregate             Photo aggregation
```

---

## Key Implementation Files

### Backend

| File | Description |
|------|-------------|
| `webui/backend/routes/export.py` | Export API endpoints |
| `webui/backend/routes/export_presets.py` | Preset API endpoints |
| `webui/backend/services/export_job_service.py` | Job queue service |
| `webui/backend/services/export_metadata_service.py` | Metadata extraction |
| `webui/backend/lib/export_job_types.py` | Job type definitions |
| `webui/backend/lib/export_job_db.py` | SQLite persistence |
| `webui/backend/lib/export_preset_types.py` | Preset type definitions |
| `webui/backend/export_preset_manager.py` | Preset CRUD operations |
| `webui/backend/lib/zip_export.py` | ZIP archive creation |
| `webui/backend/lib/photo_aggregation.py` | Photo aggregation |

### Frontend

| File | Description |
|------|-------------|
| `webui/frontend/src/pages/Export.jsx` | Main export page |
| `webui/frontend/src/components/export/` | Export components |
| `webui/frontend/src/hooks/useExportJobs.js` | Job management hooks |
| `webui/frontend/src/hooks/useExportPresets.js` | Preset management hooks |
| `webui/frontend/src/hooks/usePhotoAggregation.js` | Aggregation hook |
| `webui/frontend/src/utils/exportApi.js` | API integration |

### Presets

| File | Description |
|------|-------------|
| `webui/backend/presets_builtin/export/gbif_biodiversity.json` | GBIF preset |
| `webui/backend/presets_builtin/export/inaturalist_upload.json` | iNaturalist preset |
| `webui/backend/presets_builtin/export/simple_json.json` | JSON preset |
| `webui/backend/presets_builtin/export/simple_csv.json` | CSV preset |
| `webui/backend/presets_builtin/export/hdr_series.json` | HDR preset |
| `webui/backend/presets_builtin/export/focus_bracket_series.json` | Focus bracket preset |

---

## Related GitHub Issues

| Issue | Description | Status |
|-------|-------------|--------|
| [#112](https://github.com/zane-lazare/Mothbox/issues/112) | Export metadata service | Closed |
| [#114](https://github.com/zane-lazare/Mothbox/issues/114) | Deployment manager | Closed |
| [#116](https://github.com/zane-lazare/Mothbox/issues/116) | Darwin Core exporter | Closed |
| [#118](https://github.com/zane-lazare/Mothbox/issues/118) | iNaturalist exporter | Closed |
| [#119](https://github.com/zane-lazare/Mothbox/issues/119) | JSON/CSV exporters | Closed |
| [#122](https://github.com/zane-lazare/Mothbox/issues/122) | Export job queue | Closed |
| [#123](https://github.com/zane-lazare/Mothbox/issues/123) | Export presets | Closed |
| [#128](https://github.com/zane-lazare/Mothbox/issues/128) | ZIP optimization | Closed |
| [#129](https://github.com/zane-lazare/Mothbox/issues/129) | Export documentation | In Progress |
| [#200](https://github.com/zane-lazare/Mothbox/issues/200) | Optional deployment autofill | Closed |

---

## Error Codes Reference

| HTTP Code | Error | Resolution |
|-----------|-------|------------|
| 400 | Invalid format | Use: darwin_core, inaturalist, json, csv |
| 400 | Invalid date format | Use ISO 8601: YYYY-MM-DD |
| 400 | Invalid preset | Check preset name exists |
| 400 | No photos match filters | Adjust filter criteria |
| 403 | CSRF validation failed | Refresh page for new token |
| 403 | Invalid path | Use relative paths only |
| 404 | Job not found | Job may have expired |
| 404 | Photo not found | Check photo path |
| 429 | Rate limit exceeded | Wait 60 seconds |
| 500 | Internal server error | Check server logs |
| 503 | Service unavailable | Export service not running |

---

## Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Job creation | <100ms | Queue insertion only |
| 100 photos Darwin Core | ~10 sec | CSV generation |
| 100 photos iNaturalist | ~30 sec | With photos in ZIP |
| 100 photos JSON/CSV | ~5 sec | Metadata only |
| 1000 photos | ~1-5 min | Depends on format |
| Cache hit | <10ms | Preset lookup |
| Maximum job duration | 10 min | Configurable timeout |
| Job TTL | 1 hour | Auto-cleanup |

---

**Last Updated**: December 2024
**Version**: 1.0
