# Changelog

All notable changes to linstor-client will be documented in this file starting from version 1.13.0,
for older version see github releases.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.29.1] - 2026-08-27

### Added

- resource-definition clone: new `--volume-size` option (server REST API 1.29.1)

## [1.29.0] - 2026-08-13

### Added

- "resource-definition truncate" deletes all resources of a resource definition without deleting the resource definition itself or its snapshots; with --delete-empty-resource-definition the resource definition is deleted as well if it has no snapshots
- "snapshot delete" gained --delete-empty-resource-definition to also delete the resource definition when it has neither resources nor snapshots left after the deletion
- resource make-available: new option --auto-manage-dual-primary preparing a resource for a live migration to the given node
- New command "resource unmake-available" reverting a make-available on the migration source node after a live migration

### Changed

- "file modify" now resolves the editor like systemd: honor $EDITOR, then $VISUAL, then fall back to editor, nano, vim and vi in that order

## [1.28.1] - 2026-06-26

### Changed

- Property keys in command help output are now sorted alphabetically
- UTF-8 characters in output are now the default regardless of whether stdout is a TTY. Added --utf8 flag to explicitly set this behavior.
- Show now toggle-disk status ("Adding Disk"/"Removing Disk") to the State column of "resource list" and "volume list"

### Fixed

- "file modify" now reads back the edited content even with editors that save by replacing the file via rename
- Table: replaced low-coverage UTF-8 box-drawing glyphs with universally-supported equivalents so borders render correctly in more fonts
- "controller auth init --only-satellites" no longer crashes with KeyError when no client token is returned
- Running a command without a subcommand (e.g. "linstor volume-definition") now shows that command's subcommands instead of the full top-level command list

## [1.28.0] - 2026-05-28

### Added

- Added Satellite Platform to node list if the controller is reporting it
- Added "linstor controller export-db [EXPORT_NAME]"
- Added commands and support for linstor-controller token authentication
- Added ", Corrupt Crypt Key" Warning to "resource list" and "volume list" if needed
- Added --truncate flag to shrink table columns proportionally and truncate cells with an ellipsis when output exceeds terminal width; can also be enabled via the [global] section of the client config
- Added --drbd-client (with aliases "--drbd-diskless-client", "-c", "--client") to
  - resource create
  - resource toggle-disk
  - resource modify
- Added new column to "resource list": "Vote" that shows if a given resource has a DRBD-quorum vote
- Added (hidden by default) new column to "resource list": "Flags" that distinguishes Diskless/Tiebreaker/Client

### Changed

- Removed py2 support
- Updated build system to use python build module
- Reduced client startup overhead by lazily registering CLI subparsers
- Pipe output through a pager when the terminal is interactive
- By default "resource list" no longer shows "CreatedOn" column
- "State" column in "resource list" no longer shows "Tiebreaker" (only "Diskless" instead)
- Columns for "resource list" can now be selected via "-o" option
- resource-group list now shows also properties
- snapshot list: surface non-successful backup shipments in the State column,
  read from snapDfn properties (one line per remote in flight or failed).
  Successful shipments still display as "Successful". Requires linstor-server 1.33.0+
- r l --faulty and --all will now show all resources that include a faulty one

### Fixed

- Table: groupby/sorting raised type error if sorting column only had numbers and natsort not installed
- Fixed node interface modify defaulting communication-type to plain when not specified
- Fixed missing node connection status in node list and improve handling of unknown connection status

## [1.27.1] - 2025-12-11

### Added

- Added new alias --drbd-diskless to command "r td" to mimic the option from "r c"
- Added new sub-command "encryption status" to show the current locked-state of the controller

## [1.27.0] - 2025-11-11

### Added

- Added new option to "backup ship": --source-snapshot
- Added new option to "backup ship": --full
- Added new alias for "backup create -s": --source-snapshot
- Added --target and --do-not-target to 'node evacuate'
- from-file parameter to resource-definition list and list-properties
- from-file parameter to node lp and resource-group lp

### Fixed

- Fixed help-text for "backup restore --snapshot"

## [1.26.1] - 2025-08-26

### Added

- Added --target-resorce-name to 'backup schedule enable'

## [1.26.0] - 2025-08-18

### Added

- snapshot list and set property commands
- r l: optional --show-drbd-ports
- s rb: optional --zfs-rollback-strategy

### Changed

- rd l: Ports column now hidden by default (moved to resource level)

### Fixed

- Fixed incorrect unit in out of range error message

### Removed

- Removed "exos" commands
- Removed "snapshot ship" command. Use "backup ship" instead

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
