# Detector — Evaluation Summary

_Generated 2026-07-17T07:24:46.655208+00:00. Model: yolo11s (detection), classes: distress_candidate, out_of_water, normal_swimming._

## What the metrics support

The trained detector distinguishes the three dataset-defined visual classes (`distress_candidate`, `out_of_water`, `normal_swimming`) on held-out dataset splits. On the validation split it reaches **mAP50 0.875** (mAP50-95 0.545); on the sealed test split, **mAP50 0.773** (mAP50-95 0.453). The 0.103 validation-to-test mAP50 drop is itself informative (see the dataset caveat below).

## What the metrics do NOT support

These results do **not** establish medical drowning-detection accuracy, nor performance across all real pools, lighting, camera angles, or water clarity. "Distress" here means a visual appearance class in this dataset — not a diagnosed medical event.

## Strongest measured result

`distress_candidate` is the strongest class on validation (AP50 0.912, recall 0.846) — encouraging, because it is the safety-relevant class.

## Largest weakness

`normal_swimming` is the weakest class by validation AP50 (0.852, recall 0.835). Separately, the residual `distress_candidate` ↔ `normal_swimming` confusion is the safety-relevant error to watch: a distressed-looking swimmer occasionally reads as normal, and vice versa.

## Architectural mitigation

Because frame-level predictions may fluctuate, SwimSentinel does not convert
one YOLO prediction directly into an emergency alert. The runtime adds
anonymous tracking (ByteTrack) and temporal persistence before producing a
`SUSPECTED_DISTRESS` state, and fusion with the wearable adds independent
evidence.

## Dataset caveat

Filename analysis indicates 27 source
videos contribute frames to more than one split; about 38.9% of images
belong to such cross-split video groups. Near-duplicate frames therefore appear
in both training and evaluation, so these held-out metrics are **optimistic**
relative to a clip-independent split. Judge live runtime behaviour, not just
these numbers.

## Suggested pitch line

> SwimSentinel treats the detector as visual evidence, then applies anonymous
> tracking and temporal reasoning rather than trusting a single frame.
