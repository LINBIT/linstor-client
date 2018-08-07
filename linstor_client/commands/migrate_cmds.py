import json
import os
import sys
from linstor_client.commands import Commands
from linstor.sharedconsts import (
    VAL_NODE_TYPE_STLT,
    VAL_NODE_TYPE_CTRL,
    VAL_NODE_TYPE_AUX,
    VAL_NODE_TYPE_CMBD,
)


class MigrateCommands(Commands):
    @staticmethod
    def _header(of):
        of.write('''
### IMPORTANT: ###
# -) start with a setup where drbdmanage is in a healthy state (drbdmanage a)
# -) make sure the LINSTOR DB is empty on the controller node
# -) drbdmanage shutdown -qc # on all nodes
# -) mv /etc/drbd.d/drbdctrl.res{,.dis} # on all nodes
# -) mv /etc/drbd.d/drbdmanage-resources.res{,.dis} # on all nodes
#
# CURRENTLY THIS SCRIPT IS MISSING THESE FEATURES:
# -) snapshots (will not be supported)
# -) zfs thin pools (currenlty missing in LINSTOR)
#
# This script is meant to be reviewed for plausibility
# To make sure you did that, you have to remove the following line
exit 1\n
''')

    @staticmethod
    def lsc(of, cmd, *args):
        of.write('linstor %s %s\n' % (cmd, ' '.join(args)))

    @staticmethod
    def _get_selection(question, options):
        # py2/3
        try:
            input = raw_input
        except NameError:
            pass

        os.system('clear')
        while True:
            sys.stdout.write('%s\n\n' % (question))

            if len(options) > 0:
                for k in sorted(options.keys()):
                    sys.stdout.write('%s) %s\n' % (k, options[k]))
                ans = input('Type a number: ')
                try:
                    ans = options.get(int(ans), False)
                except ValueError:
                    continue
            else:
                ans = input('Your answer: ')

            if ans:
                return ans

    @staticmethod
    def _get_node_type(name):
        node_types = {
            1: VAL_NODE_TYPE_CTRL,
            2: VAL_NODE_TYPE_CMBD,
            3: VAL_NODE_TYPE_STLT,
            4: VAL_NODE_TYPE_AUX,
        }

        return MigrateCommands._get_selection('Node type for ' + name, node_types)

    @staticmethod
    def _create_resource(of, res_name, assg):
        for nr, v in assg.items():
            n, r = nr.split(':')
            if r == res_name:
                args = ['--node-id', str(v['_node_id']), ]
                if v['_tstate'] == 7:
                    args.append('--diskless')
                else:
                    args += ['--storage-pool', 'drbdpool']
                args += [n, r]
                MigrateCommands.lsc(of, 'resource', 'create', *args)

    @staticmethod
    def cmd_dmmigrate(args):
        try:
            inf = open(args.ctrlvol)
        except Exception as e:
            sys.stderr.write('%s\n' % e)
            return None
        try:
            of = open(args.script, 'w')
        except Exception as e:
            sys.stderr.write('%s\n' % e)
            inf.close()
            return None

        MigrateCommands._header(of)

        dm = json.load(inf)
        inf.close()

        of.write('### Nodes ###\n')
        nodes = dm['nodes']
        for n, v in nodes.items():
            MigrateCommands.lsc(of, 'node', 'create', '--node-type',
                                MigrateCommands._get_node_type(n), n, v['_addr'])
        of.write('\n')

        of.write('### Storage ###\n')
        MigrateCommands.lsc(of, 'storage-pool-definition', 'create', 'drbdpool')

        storage_types = {
            1: 'lvm',
            2: 'lvmthin',
            3: 'zfs',
            # 4: 'zfsthin',
        }
        for n, v in nodes.items():
            storage_type = MigrateCommands._get_selection('Which storage type was used on ' + n, storage_types)
            pool_name = MigrateCommands._get_selection("Volume group/pool to use on " + n + '\n\n'
                                                       "For 'lvm', the volume group name (e.g., drbdpool);\n"
                                                       "For 'zfs', the zPool name (e.g., drbdpool);\n"
                                                       "For 'lvmthin', the full name of the thin pool, namely "
                                                       "VG/LV (e.g., drbdpool/drbdthinpool);", {})
            MigrateCommands.lsc(of, 'storage-pool', 'create', n, 'drbdpool', storage_type, pool_name)

        of.write('\n')

        # resource definitions (+ port)
        res = dm['res']
        assg = dm['assg']
        for r, v in res.items():
            of.write('### Resource: %s ###\n' % (r))
            MigrateCommands.lsc(of, 'resource-definition', 'create', '--port', str(v['_port']), r)

            props = v.get('props', {})
            for prop, propval in props.items():
                for otype in ('/dso/disko/', '/dso/neto/', '/dso/peerdisko/', '/dso/reso/'):
                    if prop.startswith(otype):
                        opt = prop.split('/')[3]
                        MigrateCommands.lsc(of, 'resource-definition', 'drbd-options', '--'+opt, propval)

            volumes = v['volumes']
            vnrs = sorted([int(vnr) for vnr in volumes.keys()])
            for vnr in vnrs:
                vnr_str = str(vnr)
                vol = volumes[vnr_str]
                bdname = r+'_'
                bdname += vnr_str if vnr >= 10 else "0"+vnr_str
                MigrateCommands.lsc(of, 'volume-definition', 'create', '--vlmnr', vnr_str,
                                    '--minor', str(vol['minor']), r, str(vol['_size_kiB'])+'K')
                MigrateCommands.lsc(of, 'volume-definition', 'set-property', r, vnr_str,
                                    'OverrideVlmId', bdname)
            MigrateCommands._create_resource(of, r, assg)
            of.write('\n')

        of.close()
        sys.stdout.write('Succefully wrote %s\n' % (args.script))
        return None
