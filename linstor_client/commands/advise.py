import collections
import json
import sys

import linstor.responses
import linstor.sharedconsts as apiconsts

import linstor_client
import linstor_client.argparse.argparse as argparse
from linstor_client.commands import Commands

StateOfTheWorld = collections.namedtuple(
    'StateOfTheWorld',
    ('nodes', 'storage_pools', 'resource_groups', 'resource_definitions', 'resources', 'resource_states')
)


class _Issue(object):
    WHAT_SINGLE_REPLICA = 'Node hosts only replica of resource, would become unavailable.'
    WHAT_POTENTIAL_SPLIT_BRAIN = 'Node hosts one of 2 replicas with no tiebreaker, may lead to split-brain.'
    WHAT_NEEDLESS_DISKLESS_IN_USE = 'Resource is diskless and in-use, but a matching storage pool exists.'
    WHAT_TOO_FEW_REPLICAS_F = 'Resource expected to have {expected} replicas, got only {actual}.'
    WHAT_NO_TIEBREAKER = 'Resource has 2 replicas but no tie-breaker, could lead to split brain.'

    FIX_NEEDLESS_DISKLESS_IN_USE = 'linstor r rd --dflt {node} {rsc}'

    FIX_AUTOPLACE_TIEBREAKER = 'linstor rd ap --drbd-diskless --place-count 1 {rsc}'

    FIX_AUTOPLACE = 'linstor rd ap --place-count {count} {rsc}'

    def __init__(self, resource, what, fix):
        self.resource = resource
        self.what = what
        self.fix = fix


class AdviceCommands(Commands):
    _issue_headers = [
        linstor_client.TableHeader("Resource"),
        linstor_client.TableHeader("Issue"),
        linstor_client.TableHeader("Possible fix"),
    ]

    class Maintenance(object):
        LONG = "maintenance"
        SHORT = "m"

    def __init__(self):
        super(AdviceCommands, self).__init__()

    def setup_commands(self, parser):
        # Node subcommands
        subcmds = [
            Commands.Subcommands.Resource,
            AdviceCommands.Maintenance,
        ]

        advise_parser = parser.add_parser(
            Commands.ADVISE,
            aliases=["adv"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Advise subcommands"
        )

        advise_subp = advise_parser.add_subparsers(
            title="Advise commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmds)
        )
        p_resource = advise_subp.add_parser(
            Commands.Subcommands.Resource.LONG,
            aliases=[Commands.Subcommands.Resource.SHORT],
            description='Points out potential issues with the currently deployed resources.')
        p_resource.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_resource.add_argument('-r', '--resources', nargs='+', type=str,
                                help='Filter by list of resources').completer = self.resource_completer
        p_resource.set_defaults(func=self.resource)

        p_maintenace = advise_subp.add_parser(
            AdviceCommands.Maintenance.LONG,
            aliases=[AdviceCommands.Maintenance.SHORT],
            description='Points out potential issues should a node go down for maintenance.'
        )
        p_maintenace.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_maintenace.add_argument('-r', '--resources', nargs='+', type=str,
                                  help='Filter by list of resources').completer = self.resource_completer
        p_maintenace.add_argument('node', type=str, help='The node to check').completer = self.node_completer
        p_maintenace.set_defaults(func=self.maintenance)

        self.check_subcommands(advise_subp, subcmds)

    def resource(self, args):
        state = self._state_of_the_world()

        found_issues = []
        rsc_to_check = args.resources or state.resource_definitions.keys()

        for rsc_name in rsc_to_check:
            r_def = state.resource_definitions[rsc_name]
            rg = state.resource_groups[r_def.resource_group_name or "DfltRscGrp"]
            r_deployed = {node: r for (node, name), r in state.resources.items() if name == rsc_name}
            r_states = {node: r for (node, name), r in state.resource_states.items() if name == rsc_name}

            found_issues.extend(_check_needless_diskless(r_def, r_deployed, r_states, rg, state.storage_pools))
            found_issues.extend(_check_expected_replicas(r_def, r_deployed, r_states, rg, state.storage_pools))

        if args.machine_readable:
            json.dump([issue.__dict__ for issue in found_issues], sys.stdout)
        else:
            tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
            tbl.add_headers(AdviceCommands._issue_headers)

            for issue in found_issues:
                tbl.add_row([issue.resource, issue.what, issue.fix])
            tbl.show()

    def maintenance(self, args):
        state = self._state_of_the_world()

        found_issues = []

        rsc_to_check = args.resources or state.resource_definitions.keys()
        for rsc_name in rsc_to_check:
            if (args.node, rsc_name) not in state.resources:
                # Resource not deployed on node
                continue

            diskfull_nodes = [node for (node, name), rsc in state.resources.items()
                              if name == rsc_name and apiconsts.FLAG_DISKLESS not in rsc.flags]
            if diskfull_nodes == [args.node]:
                found_issues.append(_Issue(
                    resource=rsc_name,
                    what=_Issue.WHAT_SINGLE_REPLICA,
                    fix=_Issue.FIX_AUTOPLACE.format(rsc=rsc_name, count=2))
                )
                continue

            all_deployed = [node for (node, name), rsc in state.resources.items()
                            if name == rsc_name]

            if len(all_deployed) < 3:
                # TODO: include quorum information: if explicit quorum is set, this advise is likely wrong
                # Also, in case the node to check is diskless, we may need to advise to add another diskfull replica.
                found_issues.append(_Issue(
                    resource=rsc_name,
                    what=_Issue.WHAT_POTENTIAL_SPLIT_BRAIN,
                    fix=_Issue.FIX_AUTOPLACE_TIEBREAKER.format(rsc=rsc_name),
                ))

        if args.machine_readable:
            json.dump([issue.__dict__ for issue in found_issues], sys.stdout)
        else:
            tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
            tbl.add_headers(AdviceCommands._issue_headers)

            for issue in found_issues:
                tbl.add_row([issue.resource, issue.what, issue.fix])
            tbl.show()

    def _state_of_the_world(self):
        """
        :return: Current state of all relevant resources we can give advise on.
        :rtype: StateOfTheWorld
        """
        node_resp = self.get_linstorapi().node_list_raise()
        rg_resp = self.get_linstorapi().resource_group_list_raise()
        rd_resp = self.get_linstorapi().resource_dfn_list_raise()
        r_resp = self.get_linstorapi().resource_list_raise()
        sp_resp = self.get_linstorapi().storage_pool_list_raise()
        return StateOfTheWorld(
            {n.name: n for n in node_resp.nodes},
            {(sp.node_name, sp.name): sp for sp in sp_resp.storage_pools},
            {rg.name: rg for rg in rg_resp.resource_groups},
            {rd.name: rd for rd in rd_resp.resource_definitions},
            {(r.node_name, r.name): r for r in r_resp.resources},
            {(r.node_name, r.name): r for r in r_resp.resource_states},
        )


def _check_needless_diskless(r_def, r_deployed, r_states, rg, s_pools):
    """Checks if a resource is in-use, diskless and the resource group would allow using a storage pool on the node.

    :param linstor.responses.ResourceDefinition r_def: the resource definition to check
    :param dict[str, linstor.responses.Resource] r_deployed: the deployed resources to check
    :param dict[str, linstor.responses.ResourceState] r_states: the deployed resource states
    :param linstor.responses.ResourceGroup rg: the resource group of the resource to check
    :param dict[(str, str), linstor.responses.StoragePool] s_pools: The available storage pools
    :return: A list of issues, if any-
    :rtype: list[_Issue]
    """
    for node, rsc in r_deployed.items():
        if apiconsts.FLAG_DISKLESS not in rsc.flags:
            continue

        if not r_states.get(node, linstor.responses.ResourceState({})).in_use:
            continue

        # TODO: probably needs to smarten up about ways diskfull deployment can be blocked. right now we only check the
        # storage pools.
        available_disk_pools = [sp for (sp_node, name), sp in s_pools.items()
                                if sp_node == node and not sp.is_diskless()]

        allowed_pools = rg.select_filter.storage_pool_list or available_disk_pools

        if set(allowed_pools) & set(available_disk_pools):
            return [_Issue(
                resource=r_def.name,
                what=_Issue.WHAT_NEEDLESS_DISKLESS_IN_USE,
                fix=_Issue.FIX_NEEDLESS_DISKLESS_IN_USE.format(rsc=r_def.name, node=node),
            )]

    return []


def _check_expected_replicas(r_def, r_deployed, r_states, rg, s_pools):
    """Checks that a resource has (at-least) as many replicas deployed as if we just did an auto-place.

    :param linstor.responses.ResourceDefinition r_def: the resource definition to check
    :param dict[str, linstor.responses.Resource] r_deployed: the deployed resources to check
    :param dict[str, linstor.responses.ResourceState] r_states: the deployed resource states
    :param linstor.responses.ResourceGroup rg: the resource group of the resource to check
    :param dict[(str, str), linstor.responses.StoragePool] s_pools: The available storage pools
    :return: A list of issues, if any-
    :rtype: list[_Issue]
    """
    expected = rg.select_filter.place_count or 2

    if len(r_deployed) < expected:
        return [_Issue(
            resource=r_def.name,
            what=_Issue.WHAT_TOO_FEW_REPLICAS_F.format(expected=expected, actual=len(r_deployed)),
            fix=_Issue.FIX_AUTOPLACE.format(rsc=r_def.name, count=expected)
        )]

    if expected == 2 and len(r_deployed) == 2 and len(set(node for node, _ in s_pools.keys())) > 2:
        # TODO: should learn about ways the automatic tie breaker can be disabled
        return [_Issue(
            resource=r_def.name,
            what=_Issue.WHAT_NO_TIEBREAKER,
            fix=_Issue.FIX_AUTOPLACE_TIEBREAKER.format(rsc=r_def.name)
        )]
    return []
