# Changelog

All notable changes to linstor-client will be documented in this file starting from version 1.13.0,
for older version see github releases.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.25.4] - 2025-04-10

### Fixed

- rd clone: fix crash if --curl was set

## [1.25.3] - 2025-04-08

### Fixed

- volume-list: show empty replication states if there is no data provided

## [1.25.2] - 2025-04-08

### Changed

- replication column is now resolved by checking the replication_states map
- added --hide-replication-states column option to v l and r lv

## [1.25.1] - 2025-04-02

### Fixed

- Missing color argument in color_repl_state

## [1.25.0] - 2025-03-19

### Changed

- resource-definition-list: add more state values CLONING/FAILED...
- volume-list: show drbd replication state in its own column

### Fixed

- Incorrect environment controllers priority if given by commandline

## [1.24.0] - 2024-12-17

### Added

- Added options --target-resource-group and --force-move-resource-group to backup ship, restore and schedule enable.
- Added --layer-list argument to resource-definition clone
- Added --resource-group argument to resource-definition clone
- Added layer-list to resource-definition list

### Changed

- Column order and coloring in volume list
- Show layer-list instead of ports column in resource-list
- resource/volume list show multiple primaries as yellow

## [1.23.2] - 2024-09-25

### Fixed
- missing commands.utils package

## [1.23.1] - 2024-09-25

### Changed
- Added info text for SkipDisk scenarios
- error-report delete: allow 5d or 3d10h strings to be used for --to and --since

### Fixed
- parse_time_str/since argument: better wrong input handling

## [1.23.0] - 2024-07-11

### Added

- Autoplacer: Add --x-replicas-on-different option
- Resource delete: Add --keep-tiebreaker option

## [1.22.1] - 2024-04-25

### Changed
- encryption modify-passphrase now asks again for the new password
- non-DRBD resource now show Created instead of Unknown

### Fixed
- resource list not showing ports

## [1.22.0] - 2024-04-02

### Added
- Allow to specify options for list commands in the client config file
- Added --from-file to most list commands to read input data from a file
- Added --volume-passphrase and modify-passphrase options/commands
- Backups added --force-restore option

### Changed
- Default machine-readable output-version is now v1
- Improved command help descriptions

### Removed
- Unused vg l -R option

## [1.21.1] - 2024-02-22

### Added

- PhysicalStorageCreate: Allow zfsthin as provider kind
- Added node connectionstatus MISSING_EXT_TOOLS handler

### Fixed

- Do not hide evicted resources in volume list

### Removed

- OpenFlex commands removed

## [1.21.0] - 2024-01-22

### Added

- Added --peer-slots to "rg c", "rg m" and "rg spawn"
- Added storpool rename for schedule enable, restore and l2l shippings

### Changed

- "rg query-size-info" no longer shows 'OversubscriptionRatio' (multiple ambiguous sources)

### Fixed

- skipDisk property access on list commands

## [1.20.1] - 2023-10-25

### Added

- Add "set-log-level" subcommand for controller and node

## [1.20.0] - 2023-10-11

### Added

- Show skip-disk property and level resource list

### Changed

- Typo in remote command argument --availability-zone

### Fixed

- Fixed exos help message
- Show deleting state for DRBD_DELETE flag
- Fixed resource involved command AttributeError

## [1.19.0] - 2023-07-19

### Added

- Backup queue list command

### Changed

- `linstor -v` now shows that it is the client version

### Fixed

- Fix aux argument list handling for replicas-on-same and similar

## [1.18.0] - 2023-04-17

### Added

- Subcommand for snapshots create-multiple

### Changed

- drbd-options(opts) now correctly handle sector units

### Fixed

- RscDfn create do not ignore peerslots
- NodeCon fixed issues with path list

## [1.17.0] - 2023-03-14

### Added

- Added rg query-size-info command
- volume list: added --show-props option

### Changed

- NodeCon,RscCon: Remove DrbdOptions subcommand

### Fixed

- Improved broken pipe error handling

## [1.16.0] - 2022-12-13

### Added

- Added node connection commands

## [1.15.1] - 2022-10-18

### Added

- Snap,EBS: Added State message
- Added column for storage spaces thin for node info

### Fixed

- node info: also ignore underliners in table headers

## [1.15.0] - 2022-09-20

### Added

- Added autoplace-options to resource-group spawn command
- Added `--show-props` option to all possible list commands to add custom props columns
- Added commands for the key-value-stora API
- Added SED support in the physical-storage-create command
- Added EBS support/commands
- Advise added too many replicas issue and filtering by issue type

### Fixed

- Fixed typos in vd help

## [1.14.0] - 2022-07-06

### Added

- Added commands for backup schedule
- SOS-Report: Added filters
- Added backup delete `keep-snaps` option

## [1.13.1] - 2022-05-12

### Changed

- file editor fallback switched to nano

### Fixes

- Fixed loading remotes with ETCD backend
- Autosnapshot: fix property not working on RG or controller

## [1.13.0] - 2022-05-22

### Added

- Added ZFS clone option for clone resource-definition
- Added resource-definition wait sync command
- Added backup snapshot name
- Added controller backup DB command
- Show resource/snapshot for backups
