# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]


## [1.1.0] - 2025-07-06

### Changed
- Authentication.py to better handle data synchronisation with Clerk
- Admin.py to register newly introduced models


### Deprecated

### Added

### Removed


## 2025-08-21

### Changed
- Refactored transition_pending_delete_to_delted task to remove ideaOfTheDay logic

### Added
- Created a new update_idea_of_the_day task to independently handle ideaoftheday assignment deterministically at midnight daily
- Added a new migration file to implement the change in the periodic tasks
