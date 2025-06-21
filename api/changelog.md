# Changelog

## [Unreleased] - Django Model & Loader Refactoring

### Added
- Implemented `drop_date` as a required CLI argument in the custom data loader (`load_json.py`).
- Auto-calculation of `drop_time` based on domain extension in the `Name` model (`.com`, `.co`, `.io`, `.ai`).
- Post-save signals to compute and assign `competition`, `difficulty`, and `suggested_usecase` for each `Name` instance after related `UseCase` objects are saved.
- Dynamic assignment of `status` field in the loader based on the provided `--domain_list` argument:
  - Automatically set to `'pending'` for the `pending_delete` domain list.
  - Automatically set to `'available'` for the `marketplace` domain list.
- Integrated comprehensive logging into `load_json.py` to record key processing steps, errors, and successes.
- Enhanced JSON validation via `validators.py`:
  - Enforced required fields and types.
  - Limited `use_cases` entries to a maximum of 3 per domain.
  - Removed validation dependency on fields that are model defaults, computed, or signal-driven (e.g., `competition`, `difficulty`, `suggested_usecase`, `drop_time`, `extension`, `is_top_rated`, `is_favorite`, `status`).

### Changed
- Refactored `Name` model:
  - Removed `use_cases` ManyToManyField (now accessed via reverse ForeignKey relation `use_cases_domain`).
  - `drop_time` is now non-editable and computed automatically in the model's `save()` method.
  - Made `competition`, `difficulty`, and `suggested_usecase` nullable to allow post-save signal processing.
- Refactored `load_json.py` loader:
  - Enforced provision of `--drop_date` argument during data load.
  - Validates presence and format of `drop_date`; raises error if missing or invalid.
  - Automatically determines `status` based on the `--domain_list` CLI option.
  - Processes `category` from nested JSON object (`{ "category": { "name": "" } }`).
  - Clears and updates `tags` (ManyToMany).
  - Deletes and recreates related `UseCase` entries per `Name`.
  - Removed redundant fields (`competition`, `difficulty`, `suggested_usecase`, `extension`, `drop_time`, `is_top_rated`, `is_favorite`, `status`) from expected JSON input, as they are now set via model defaults, methods, or signals.
  - Implemented detailed logging to track progress and catch errors during data load.

### Fixed
- Prevented circular saving or infinite loops in model save methods and signals.
- Ensured consistent and correct `drop_time` computation per domain extension.
- Corrected misuse of `DomainListOptions` Enum in `load_json.py` argument parsing.

### Notes
- The `load_json.py` file must reside in the correct Django structure: `management/commands/`.
- Data loading command example:

```bash
python manage.py load_json api/data/date.json --drop_date=2025-07-01
