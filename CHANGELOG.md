# Changelog

All notable changes to linstor-client will be documented in this file starting from version 1.13.0,
for older version see github releases.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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