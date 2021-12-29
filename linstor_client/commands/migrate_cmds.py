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
    _pool = 'drbdpool'

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
#
# If the controller is not executed on the local host, set this variable:
LS_CONTROLLERS="localhost"
export LS_CONTROLLERS
#
# This script is meant to be reviewed for plausibility
# To make sure you did that, you have to remove the following line
echo "migration disabled, review script and remove this line"; exit 1\n
''')

    @staticmethod
    def lsc(of, cmd, *args):
        of.write('linstor %s %s\n' % (cmd, ' '.join(args)))

    @staticmethod
    def _get_selection(question, options, default=''):
        # py2/3
        if sys.version_info < (3,):
            my_input = raw_input
        else:
            my_input = input

        def ask(prefix):
            if default:
                prefix += ' or <Enter> for "%s"' % default
            answer = my_input('%s: ' % prefix)
            if answer == '':  # <Enter>
                return default  # which is the set default or ''
            return answer

        os.system('clear')
        while True:
            sys.stdout.write('%s\n\n' % question)

            if len(options) > 0:
                for k in sorted(options.keys()):
                    sys.stdout.write('%s) %s\n' % (k, options[k]))
                ans = ask('Type a number')
                try:
                    if ans != default:
                        ans = options.get(int(ans), False)
                except ValueError:
                    continue
            else:
                ans = ask('Your answer')

            if ans:
                return ans

    @staticmethod
    def _get_node_type(name, default=''):
        node_types = {
            1: VAL_NODE_TYPE_CTRL,
            2: VAL_NODE_TYPE_CMBD,
            3: VAL_NODE_TYPE_STLT,
            4: VAL_NODE_TYPE_AUX,
        }

        return MigrateCommands._get_selection('Node type for ' + name, node_types, default)

    @staticmethod
    def _create_resource(of, res_name, assg):
        overall_args = []
        for nr, v in assg.items():
            n, r = nr.split(':')
            if r == res_name:
                diskless = False
                args = ['--node-id', str(v['_node_id']), ]
                if v['_tstate'] == 7:
                    args.append('--diskless')
                    diskless = True
                else:
                    args += ['--storage-pool', MigrateCommands._pool]
                args += [n, r]

                # order does not really matter, but we want at least one node with disk
                # before we create the first diskless.
                if diskless:
                    overall_args.append(args)
                else:
                    overall_args.insert(0, args)

        needs_transaction = True if len(overall_args) > 1 else False

        if needs_transaction:
            MigrateCommands.lsc(of, 'resource', 'create-transactional',
                                'begin', '--terminate-on-error', '<<EOF')
        for args in overall_args:
            MigrateCommands.lsc(of, 'resource', 'create', *args)
        if needs_transaction:
            MigrateCommands.lsc(of, 'resource', 'create-transactional', 'commit')
            of.write('EOF\n')

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
        node_type = ''
        for n, v in nodes.items():
            node_type = MigrateCommands._get_node_type(n, node_type)
            MigrateCommands.lsc(of, 'node', 'create', '--node-type', node_type, n, v['_addr'])
        of.write('\n')

        of.write('### Storage ###\n')
        MigrateCommands._pool = MigrateCommands._get_selection(
            'Name of the storage pool\n\nThis does not have to match an existing LVM pool\n'
            'it is just a name to summarize individual pools of nodes in LINSTOR\n'
            'if unsure, just go for the default',
            {}, 'drbdpool'
        )

        NONE = 'NONE'
        storage_types = {
            0: NONE,
            1: 'lvm',
            2: 'lvmthin',
            3: 'zfs',
            4: 'zfsthin',
        }
        storage_type, pool_name = '', ''
        for n, v in nodes.items():
            storage_type = MigrateCommands._get_selection('Which storage type was used on ' + n + '\n\n'
                                                          'Use NONE if this node does not have storage\n'
                                                          'NONE is used for example for plain hypervisor nodes',
                                                          storage_types, storage_type)
            if storage_type == NONE:
                of.write('# %s has no storage (e.g., hypervisor node)\n' % (n))
                continue

            pool_name = MigrateCommands._get_selection("Volume group/pool to use on " + n + '\n\n'
                                                       "For 'lvm', the volume group name (e.g., drbdpool);\n"
                                                       "For 'zfs' or 'zfsthin', the zPool name (e.g., drbdpool);\n"
                                                       "For 'lvmthin', the full name of the thin pool, namely "
                                                       "VG/LV (e.g., drbdpool/drbdthinpool);", {}, pool_name)
            MigrateCommands.lsc(of, 'storage-pool', 'create', storage_type, n,
                                MigrateCommands._pool, pool_name)

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
                        MigrateCommands.lsc(of, 'resource-definition', 'drbd-options', '--' + opt, propval, r)

            volumes = v['volumes']
            vnrs = sorted([int(vnr) for vnr in volumes.keys()])
            for vnr in vnrs:
                vnr_str = str(vnr)
                vol = volumes[vnr_str]
                bdname = r + '_'
                bdname += vnr_str if vnr >= 10 else "0" + vnr_str
                MigrateCommands.lsc(of, 'volume-definition', 'create', '--vlmnr', vnr_str,
                                    '--minor', str(vol['minor']), r, str(vol['_size_kiB']) + 'K')
                MigrateCommands.lsc(of, 'volume-definition', 'set-property', r, vnr_str,
                                    'OverrideVlmId', bdname)
                cgi = vol.get('props', {}).get('current-gi', None)
                if cgi is not None:
                    MigrateCommands.lsc(of, 'volume-definition', 'set-property', r, vnr_str,
                                        'DrbdCurrentGi', '{:0>16}'.format(cgi))

            MigrateCommands._create_resource(of, r, assg)
            of.write('\n')

        of.close()
        sys.stdout.write('Successfully wrote %s\n' % (args.script))
        return None
