# Data Validation Specification

## Purpose

To ensure that all incoming market data and research inputs are correct, consistent and reliable, the system must include a modular data validation layer.  Validators operate on typed data models and produce a validation report detailing errors, warnings and metrics.

## Functional Requirements

* **Schema Validation** – Check that incoming data conforms to the expected schema (e.g., required columns exist, correct types).  For example, funding rate objects must have `timestamp`, `symbol`, and `rate` fields.
* **Missingness Checks** – Verify that critical fields (price, size, side) are not null; handle missing optional fields gracefully.
* **Bounds & Range Checks** – Ensure values fall within plausible ranges (e.g., funding rates ±4 %【438442747367044†L104-L116】, liquidation sizes non‑negative).  Flag values outside bounds.
* **Monotonic Timestamps** – Confirm that timestamp sequences are strictly increasing; detect out‑of‑order events.
* **Duplicate Detection** – Identify duplicate events based on primary key (timestamp+ID) and optionally merge or discard duplicates.
* **Outlier Flagging** – Apply basic statistical checks (e.g., Z‑score) to flag extreme values for review; thresholds should be configurable per data type.
* **Validation Report** – Each validation run returns a structured report with counts of errors, warnings and flagged outliers.  Reports must be serialisable for logging.

## Non‑Functional Requirements

* **Deterministic** – Validation results must be reproducible across runs given the same input.
* **Performance** – Validators should process at least 10 k events per second on consumer hardware; caching intermediate results is encouraged.
* **Extensibility** – Users should be able to register custom validators via a plugin interface (e.g., `validators.register(MyValidator)`).

## Implementation Notes

* Define a base `Validator` class in `validators/base.py` with a `validate(data: Iterable) -> ValidationReport` method.
* Implement built‑in validators: `SchemaValidator`, `MissingnessValidator`, `RangeValidator`, `MonotonicValidator`, `DuplicateValidator`, `OutlierValidator`.
* Provide fixtures and tests in `tests/validators` to ensure each validator behaves as expected.
* Expose a command (e.g., `:validate <dataset>`) to run validation on a snapshot and display a summary table.
