#!/usr/bin/env python3
import os
import argparse
import subprocess
import csv
import json
import http.client
import logging
import sys
from datetime import datetime
from typing import Optional, Tuple

"""
This script helps checking LINSTOR if there are orphaned CloudStack resources.
It will dump data out of the cloudstack database in the /tmp directory and then check against
the LINSTOR controller if expunged resources are still in LINSTOR.
If so it will output commands to remove them.
"""

logging.basicConfig(format='%(asctime)-15s %(levelname)s:%(name)s:%(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

_CS_PREFIX = "cs-"
_DUMP_PATH = "/tmp/linstor-cloudstack"
_TEMPLATE_VOLUME_CSV_PATH = _DUMP_PATH + "/cs_template_volumes.csv"
_VOLUMES_CSV_PATH = _DUMP_PATH + "/cs_volumes.csv"
_POOL_CSV_PATH = _DUMP_PATH + "/cs_storage_pool.csv"
_SNAPSHOTS_PATH = _DUMP_PATH + "/cs_snapshots.csv"
_VM_SNAPSHOTS_PATH = _DUMP_PATH + "/cs_vm_snapshots.csv"


class CSVolumeSnapshot:
    def __init__(self, id_: int, volume_id: int, name: str, uuid: str, state: str):
        self._id = id_
        self._name = name
        self._uuid = uuid
        self._state = state
        self._volume_id = volume_id

    @property
    def uuid(self):
        return self._uuid

    @property
    def volume_id(self):
        return self._volume_id

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    def __repr__(self):
        return f"VolumeSnapshot({self._uuid},{self._volume_id},'{self._name}',{self._state})"


class CSVMSnapshot:
    def __init__(self, id_: int, name: str, uuid: str, state: str):
        self._id = id_
        self._name = name
        self._uuid = uuid
        self._state = state

    @property
    def uuid(self):
        return self._uuid

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    def __repr__(self):
        return f"CSVMSnapshot({self._uuid},'{self._name}',{self._state})"


class CSResource:
    def __init__(self, id_: int, name: str, uuid: str, state: str, snapshots: list[CSVolumeSnapshot]):
        self._id = id_
        self._name = name
        self._uuid = uuid
        self._state = state
        self._snapshots = snapshots

    @property
    def uuid(self):
        return self._uuid

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def snapshots(self):
        return self._snapshots

    def __repr__(self):
        return f"Resource({self._uuid},'{self._name}',{self._state},{self._snapshots})"

class LinSnapshot:
    def __init__(self, rsc_name: str, name: str, create_timestamp: int):
        self._rsc_name = rsc_name
        self._name = name
        self._referred = False
        self._create_dt = datetime.fromtimestamp(create_timestamp / 1000)

    @property
    def rsc_name(self):
        return self._rsc_name

    @property
    def name(self):
        return self._name

    @property
    def create_dt(self):
        return self._create_dt

    @property
    def referred(self):
        return self._referred

    @referred.setter
    def referred(self, val):
        self._referred = val

    def __repr__(self):
        return f"LinSnapshot({self._rsc_name},'{self._name},{self._referred}')"

def error_exit(msg: str):
    print(msg, file=sys.stderr)
    sys.exit(1)

def load_cs_resources() -> Tuple[list[CSResource], list[CSVMSnapshot]]:
    vm_snapshots = []
    with open(_VM_SNAPSHOTS_PATH) as csvfile:
        rdr = csv.reader(csvfile, dialect='unix')
        for row in rdr:
            vm_snapshots.append(CSVMSnapshot(int(row[0]), row[1], row[2], row[3]))

    snapshots = []
    with open(_SNAPSHOTS_PATH) as csvfile:
        rdr = csv.reader(csvfile, dialect='unix')
        for row in rdr:
            snapshots.append(CSVolumeSnapshot(int(row[0]), int(row[1]), row[2], row[3], row[4]))

    resources = []
    read_files = [_TEMPLATE_VOLUME_CSV_PATH, _VOLUMES_CSV_PATH]
    for file in read_files:
        with open(file) as csvfile:
            rdr = csv.reader(csvfile, dialect='unix')
            for row in rdr:
                cs_uuid = row[2]
                if cs_uuid != '\\N':
                    volume_id = int(row[0])
                    volume_snaps = [x for x in snapshots if volume_id == x.volume_id]
                    resources.append(CSResource(volume_id, row[1], cs_uuid, row[3], volume_snaps))
    return resources, vm_snapshots

def get_linstor_cs_resources(controller: str) -> list[str]:
    conn = http.client.HTTPConnection(controller)
    try:
        conn.request("GET", "/v1/resource-definitions")
        rd_res = conn.getresponse()
        if rd_res.status == 200:
            data = json.load(rd_res)
            lin_rs = [x['name'] for x in data if x['name'].startswith(_CS_PREFIX)]
            return lin_rs
        else:
            raise ValueError("request resource-definitions error")
    except ConnectionRefusedError:
        error_exit(f"Linstor-Controller '{controller}' can't be reached.")
    finally:
        conn.close()

def get_linstor_cs_snapshots(controller: str) -> list[LinSnapshot]:
    # out = subprocess.check_output(["linstor", "--controllers", controller, "-m", "rd", "l"])
    # data = json.loads(out)
    conn = http.client.HTTPConnection(controller)
    try:
        conn.request("GET", "/v1/view/snapshots")
        rd_res = conn.getresponse()
        if rd_res.status == 200:
            data = json.load(rd_res)
            lin_rs = [LinSnapshot(x['resource_name'], x['name'], x['snapshots'][0]['create_timestamp']) for x in data if x['resource_name'].startswith(_CS_PREFIX)]
            return lin_rs
        else:
            raise ValueError("request snapshots error")
    except ConnectionRefusedError:
        error_exit(f"Linstor-Controller '{controller}' can't be reached.")
    finally:
        conn.close()

class DBDumper:
    _TEMPLATE_SQL = "SELECT tsr.id, vt.name, tsr.install_path, tsr.state FROM template_spool_ref tsr JOIN vm_template vt ON vt.id=tsr.template_id WHERE pool_id={pool_id}"
    _VOLUME_SQL = "SELECT id, name, path, state FROM volumes WHERE pool_id={pool_id}"
    _SNAPSHOTS_SQL = "SELECT id, volume_id, name, uuid, status FROM snapshots"
    _VM_SNAPSHOTS_SQL = "SELECT id, name, uuid, state FROM vm_snapshots"
    _STORAGE_POOL_SQL = "SELECT id FROM storage_pool WHERE pool_type='Linstor' AND removed IS NULL and status='Up'"
    _FIND_POOL_SQL = "SELECT id FROM storage_pool WHERE pool_type='Linstor' AND uuid='{pool_uuid}'"

    _INTO_CSV_FILE_SQL = " INTO OUTFILE '{outfile}' FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '\"';"

    def __init__(self, bin_name: str, db: str, pool_uuid: Optional[str]):
        self._bin_name = bin_name
        self._db = db
        self._pool_id = 0  # fake

        if not os.path.exists(_DUMP_PATH):
            os.mkdir(_DUMP_PATH)

        if pool_uuid is None:
            self._pool_id = self._get_first_linstor_pool_id()
        else:
            self._pool_id = self._find_pool_id(pool_uuid)
        if not self._pool_id:
            raise RuntimeError("Pool id not found")

    def _query_db(self, select_stmt: str, out_csv_file: str):
        exec_stmt = select_stmt.format(pool_id=self._pool_id) + DBDumper._INTO_CSV_FILE_SQL.format(outfile=out_csv_file)
        cpr = subprocess.run([self._bin_name, self._db], input=exec_stmt.encode())
        cpr.check_returncode()

    def dump_info(self):
        for rmpath in [_TEMPLATE_VOLUME_CSV_PATH, _VOLUMES_CSV_PATH, _SNAPSHOTS_PATH, _VM_SNAPSHOTS_PATH]:
            if os.path.exists(rmpath):
                os.remove(rmpath)

        self._query_db(DBDumper._TEMPLATE_SQL, _TEMPLATE_VOLUME_CSV_PATH)
        self._query_db(DBDumper._VOLUME_SQL, _VOLUMES_CSV_PATH)
        self._query_db(DBDumper._SNAPSHOTS_SQL, _SNAPSHOTS_PATH)
        self._query_db(DBDumper._VM_SNAPSHOTS_SQL, _VM_SNAPSHOTS_PATH)

    def _get_first_linstor_pool_id(self):
        if os.path.exists(_POOL_CSV_PATH):
            os.remove(_POOL_CSV_PATH)
        self._query_db(DBDumper._STORAGE_POOL_SQL, _POOL_CSV_PATH)
        with open(_POOL_CSV_PATH) as pool_file:
            data = pool_file.readline(1).strip()
            if data:
                return int(data)
            else:
                raise RuntimeError("Error finding first Linstor pool")

    def _find_pool_id(self, uuid: str):
        if os.path.exists(_POOL_CSV_PATH):
            os.remove(_POOL_CSV_PATH)
        self._query_db(DBDumper._FIND_POOL_SQL.format(pool_uuid=uuid), _POOL_CSV_PATH)
        with open(_POOL_CSV_PATH) as pool_file:
            data = pool_file.readline(1).strip()
            if data:
                return int(data)
            else:
                raise RuntimeError("Unable to find pool id for UUID: " + uuid)

def main():
    parser = argparse.ArgumentParser(
        description="Helper script to check for orphaned CloudStack resource in Linstor."
                    "You need a local db client (mariadb|mysql) with access to cloud db and the url to the "
                    "linstor-controller")
    parser.add_argument("--db-bin", default="mariadb", help="db client binary to use (mariadb|mysql)")
    parser.add_argument("--db", default="cloud", help="Database name of the CloudStack db")
    parser.add_argument("--skip-dump", action="store_true", help="Do not dump DB data, needs data in /tmp")
    parser.add_argument("--cs-pool-uuid", default=None, type=str, help="CloudStack primary storage UUID")
    parser.add_argument("--verbose", "-v", action="store_true", help="Debug logging")
    parser.add_argument("controller", nargs='?', default="localhost:3370",
                        help="Linstor controller host:port of the primary storage")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if not args.skip_dump:
        logger.debug("Dumping DB data...")
        db_dumper = DBDumper(args.db_bin, args.db, args.cs_pool_uuid)
        db_dumper.dump_info()

    logger.debug("Loading CS data...")
    cs_resources, cs_vm_snapshots = load_cs_resources()

    active_vm_snapshots = [x.name for x in cs_vm_snapshots if x.state == 'Ready']
    active_volume_snapshots = [_CS_PREFIX + x.uuid for x in [snapshot for y in cs_resources
                                                for snapshot in y.snapshots if snapshot.state == 'BackedUp']]
    error_volume_snapshots = [_CS_PREFIX + x.uuid for x in [snapshot for y in cs_resources
                                                for snapshot in y.snapshots if snapshot.state == 'Error']]
    destroyed_volume_snapshots = [_CS_PREFIX + x.uuid for x in [snapshot for y in cs_resources
                                                for snapshot in y.snapshots if snapshot.state == 'Destroyed']]

    # print(repr(cs_resources))
    # print(repr(cs_vm_snapshots))
    # print(active_volume_snapshots)

    # print("Found Following CS Resources")
    # print("{uuid:36} {name:50} state".format(uuid="UUID", name="NAME"))
    # for res in cs_resources:
    #     print(f"{res.uuid} {res.name:50} {res.state}")

    logger.debug("Fetching LINSTOR data...")
    lin_resources = get_linstor_cs_resources(args.controller)

    lin_snapshots = get_linstor_cs_snapshots(args.controller)

    logger.debug("Checking for orphaned...")
    cs_expunged = [x for x in cs_resources if x.state.lower() == 'expunged']

    for lin_snap in lin_snapshots:
        if lin_snap.name in active_vm_snapshots:
            lin_snap.referred = True

    orphaned_snaps = [x for x in lin_snapshots if not x.referred]

    orphaned_snaps.sort(key=lambda x: x.create_dt)
    if orphaned_snaps:
        print("The following snapshots are not actively referred in CloudStack, but are still present in LINSTOR:\n")
        print("created at          rsc-name                                snapshot-name                           cs-state")
        for x in orphaned_snaps:
            state = "unknown"
            if x.name in active_volume_snapshots:
                state = "backedup"
            elif x.name in error_volume_snapshots:
                state = "error"
            elif x.name in destroyed_volume_snapshots:
                state = "destroyed"
            identifier = x.rsc_name + " " + x.name
            print(f"{x.create_dt.isoformat()[0:19]} {identifier:79} {state}")
        print()
        print("-" * 80)
        print("To delete run the following command:")
        for x in orphaned_snaps:
            print(f"linstor s d {x.rsc_name} {x.name}")

    still_in_linstor = [x for x in cs_expunged if (_CS_PREFIX + x.uuid).lower() in lin_resources]
    if still_in_linstor:
        print("The following resources are expunged in CloudStack, but are still present in LINSTOR:\n")
        print("\n".join([repr(x) for x in still_in_linstor]))
        print("-" * 80)
        print("To delete run the following command:")
        print("linstor rd d " + " ".join([_CS_PREFIX + x.uuid for x in still_in_linstor]))

if __name__ == "__main__":
    main()
