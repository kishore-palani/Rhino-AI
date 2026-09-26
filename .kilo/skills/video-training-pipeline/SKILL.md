---
name: video-training-pipeline
description: Use when building the video ingestion, processing, annotation, evaluation, or training-data pipeline that learns architectural CAD workflows from raw videos.
---

# Video-to-Training-Data Pipeline

Treat each output as a derived, traceable artifact. Keep raw media immutable and
separate from processed files, metadata, datasets, and model-training exports.
Use the existing `data/raw/`, `data/processed/`, `data/metadata/`, `data/datasets/`
and `scripts/processing/` structure unless current code establishes a better
owner.

## Staged artifacts

Model the pipeline as explicit stages that can be rerun independently:

1. Ingest media metadata, source/license information, checksum, duration, and
   codec without silently duplicating raw assets.
2. Segment by timestamp and retain stable source-time offsets.
3. Extract transcript and OCR with engine/version and confidence metadata.
4. Detect visible CAD actions and associate them with time ranges; distinguish
   observed UI events from inferred design intent.
5. Link action sequences to before/after geometry or project files only when
   those artifacts are available and provenance is clear.
6. Export versioned, validated examples for retrieval or training.

## Engineering requirements

- Make stages idempotent, resumable, and safe to retry.
- Persist source IDs, time ranges, tool/model versions, parameters, confidence,
  and transformation lineage.
- Represent uncertainty and missing evidence explicitly; do not promote model
  guesses to ground-truth labels.
- Respect copyright, privacy, consent, and data-retention constraints for raw
  videos and derived transcripts.
- Keep unit tests small and deterministic with synthetic media metadata or
  fixtures. Do not require network, GPU, or large source videos in CI.
- Check `requirements.txt` and existing provider abstractions before adding a
  new speech, OCR, vision, or video dependency. Document optional system tools
  such as FFmpeg rather than assuming they are installed.

Evaluate extraction quality against labeled examples and report errors by
stage. A successful pipeline run is not evidence that inferred design reasoning
is correct.