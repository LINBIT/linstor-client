import json
import sys
from linstor.commands import Commands
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
# -) make sure the LINSTOR DB is empty on *all* nodes
# -) drbdmanage shutdown -qc # on all nodes
# -) mv /etc/drbd.d/drbdctrl.res{,.dis} # on all nodes
# -) mv /etc/drbd.d/drbdmanage-resources.res{,.dis} # on all nodes
#
# CURRENTLY THIS SCRIPT IS MISSING THESE FEATURES:
# -) snapshots
# -) zfs pools
#
# This script is meant to reviewed for plausibility execution
# To make sure you did that, you have to remove the following line
exit 1\n
''')

    @staticmethod
    def lsc(of, cmd, *args):
        of.write('linstor %s %s\n' % (cmd, ' '.join(args)))

    @staticmethod
    def _get_node_type(name):
        node_types = {
            1: VAL_NODE_TYPE_CTRL,
            2: VAL_NODE_TYPE_AUX,
            3: VAL_NODE_TYPE_AUX,
            4: VAL_NODE_TYPE_STLT,
        }
        # py2/3
        try:
            input = raw_input
        except NameError:
            pass

        while True:
            sys.stdout.write('\nNode type for %s\n' % (name))
            for k in sorted(node_types.keys()):
                sys.stdout.write('%s) %s\n' % (k, node_types[k]))
            ans = input('Type a number: ')
            try:
                ans = node_types.get(int(ans), False)
            except ValueError:
                continue
            if ans:
                return ans

    @staticmethod
    def _create_resource(of, res_name, assg):
        for nr, v in assg.items():
            n, r = nr.split(':')
            if r == res_name:
                args = ['--nodeid', str(v['_node_id']), '--storage-pool', 'drbdpool']
                if v['_tstate'] == 7:
                    args.append('--diskless')
                args += [r, n]
                MigrateCommands.lsc(of, 'create-resource', *args)

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
            MigrateCommands.lsc(of, 'create-node', '--node-type',
                                MigrateCommands._get_node_type(n), n, v['_addr'])
        of.write('\n')

        # resource definitions (+ port)
        res = dm['res']
        assg = dm['assg']
        for r, v in res.items():
            of.write('### Resource: %s ###\n' % (r))
            MigrateCommands.lsc(of, 'create-resource-definition', '--port', str(v['_port']), r)
            volumes = v['volumes']
            vnrs = sorted([int(vnr) for vnr in volumes.keys()])
            for vnr in vnrs:
                vol = volumes[str(vnr)]
                vnr_str = str(vnr)
                MigrateCommands.lsc(of, 'create-volume-definition', '--volnr', vnr_str,
                                    '--minor', str(vol['minor']), r, str(vol['_size_kiB'])+'K')
                MigrateCommands.lsc(of, 'set-volume-definition-aux-prop', r, vnr_str, 'drbdmanage-compat', 'on')
            MigrateCommands._create_resource(of, r, assg)
            of.write('\n')

        of.close()
        sys.stdout.write('Succefully wrote %s\n' % (args.script))
        return None
