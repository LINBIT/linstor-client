from proto.MsgCrtRscDfn_pb2 import MsgCrtRscDfn
from proto.MsgDelRscDfn_pb2 import MsgDelRscDfn
from proto.MsgLstRscDfn_pb2 import MsgLstRscDfn
from linstor.commcontroller import need_communication, completer_communication
from linstor.commands import Commands
from linstor.utils import rangecheck, namecheck, Table, Output
from linstor.sharedconsts import (
    API_CRT_RSC_DFN,
    API_DEL_RSC_DFN,
    API_LST_RSC_DFN,
    FLAG_DELETE
)
from linstor.consts import RES_NAME, Color


class ResourceDefinitionCommands(Commands):

    @staticmethod
    def setup_commands(parser):
        p_new_res_dfn = parser.add_parser(
            'create-resource-definition',
            aliases=['crtrscdfn'],
            description='Defines a Linstor resource definition for use with linstor.')
        p_new_res_dfn.add_argument('-p', '--port', type=rangecheck(1, 65535))
        # p_new_res_dfn.add_argument('-s', '--secret', type=str)
        p_new_res_dfn.add_argument('name', type=namecheck(RES_NAME), help='Name of the new resource definition')
        p_new_res_dfn.set_defaults(func=ResourceDefinitionCommands.create)

        # remove-resource definition
        # TODO description
        p_rm_res_dfn = parser.add_parser(
            'delete-resource-definition',
            aliases=['delrscdfn'],
            description=" Removes a resource definition "
            "from the linstor cluster. The resource is undeployed from all nodes "
            "and the resource entry is marked for removal from linstor's data "
            "tables. After all nodes have undeployed the resource, the resource "
            "entry is removed from linstor's data tables.")
        p_rm_res_dfn.add_argument('-q', '--quiet', action="store_true",
                                  help='Unless this option is used, linstor will issue a safety question '
                                  'that must be answered with yes, otherwise the operation is canceled.')
        p_rm_res_dfn.add_argument(
            'name',
            nargs="+",
            help='Name of the resource to delete').completer = ResourceDefinitionCommands.completer
        p_rm_res_dfn.set_defaults(func=ResourceDefinitionCommands.delete)

        resverbose = ('Port',)
        resgroupby = ('Name', 'Port', 'State')
        res_verbose_completer = Commands.show_group_completer(resverbose, "show")
        res_group_completer = Commands.show_group_completer(resgroupby, "groupby")

        p_lrscdfs = parser.add_parser(
            'list-resource-definitions',
            aliases=['list-resource-definition', 'dsprscdfn', 'display-resource-definitions', 'resource-definitions',
                     'dsprscdfn'],
            description='Prints a list of all resource definitions known to '
            'linstor. By default, the list is printed as a human readable table.')
        p_lrscdfs.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lrscdfs.add_argument('-s', '--show', nargs='+',
                               choices=resverbose).completer = res_verbose_completer
        p_lrscdfs.add_argument('-g', '--groupby', nargs='+',
                               choices=resgroupby).completer = res_group_completer
        p_lrscdfs.add_argument('-R', '--resources', nargs='+', type=namecheck(RES_NAME),
                               help='Filter by list of resources').completer = ResourceDefinitionCommands.completer
        p_lrscdfs.set_defaults(func=ResourceDefinitionCommands.list)

        # show properties
        p_sp = parser.add_parser(
            'get-resource-definition-properties',
            aliases=['get-resource-definition-props', 'dsprscdfnprp'],
            description="Prints all properties of the given resource definitions.")
        p_sp.add_argument(
            'resource_name',
            help="Resource definition for which to print the properties"
        ).completer = ResourceDefinitionCommands.completer
        p_sp.set_defaults(func=ResourceDefinitionCommands.print_props)

    @staticmethod
    @need_communication
    def create(cc, args):
        p = MsgCrtRscDfn()
        p.rsc_dfn.rsc_name = args.name
        if args.port:
            p.rsc_dfn.rsc_dfn_port = args.port
        # if args.secret:
        #     p.secret = args.secret

        return Commands._create(cc, API_CRT_RSC_DFN, p, args)

    @staticmethod
    @need_communication
    def delete(cc, args):
        del_msgs = []
        for rsc_name in args.name:
            p = MsgDelRscDfn()
            p.rsc_name = rsc_name

            del_msgs.append(p)

        return Commands._delete_and_output(cc, args, API_DEL_RSC_DFN, del_msgs)

    @staticmethod
    @need_communication
    def list(cc, args):
        lstmsg = Commands._get_list_message(cc, API_LST_RSC_DFN, MsgLstRscDfn(), args)

        if lstmsg:
            tbl = Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
            tbl.add_column("ResourceName")
            tbl.add_column("Port")
            tbl.add_column("State", color=Output.color(Color.DARKGREEN, args.no_color))
            for rsc_dfn in lstmsg.rsc_dfns:
                tbl.add_row([
                    rsc_dfn.rsc_name,
                    rsc_dfn.rsc_dfn_port,
                    tbl.color_cell("DELETING", Color.RED)
                    if FLAG_DELETE in rsc_dfn.rsc_dfn_flags else tbl.color_cell("ok", Color.DARKGREEN)
                ])
            tbl.show()

            # prntfrm = "{rsc:<20s} {port:<10s} {uuid:<40s}"
            # print(prntfrm.format(rsc="Resource-name", port="Port", uuid="UUID"))
            # for rsc_dfn in lstmsg.rsc_dfns:
            #     print(prntfrm.format(rsc=rsc_dfn.rsc_name,
            #           port=str(rsc_dfn.rsc_dfn_port), uuid=rsc_dfn.rsc_dfn_uuid))

        return None

    @staticmethod
    @need_communication
    def print_props(cc, args):
        lstmsg = Commands._request_list(cc, API_LST_RSC_DFN, MsgLstRscDfn())

        if lstmsg:
            for rsc_dfn in lstmsg.rsc_dfns:
                if rsc_dfn.rsc_name == args.resource_name:
                    Commands._print_props(rsc_dfn.rsc_dfn_props)
                    break

        return None

    @staticmethod
    @completer_communication
    def completer(cc, prefix, **kwargs):
        possible = set()
        lstmsg = Commands._get_list_message(cc, API_LST_RSC_DFN, MsgLstRscDfn())

        if lstmsg:
            for rsc_dfn in lstmsg.resources:
                possible.add(rsc_dfn.rsc_name)

            if prefix:
                return [res for res in possible if res.startswith(prefix)]

        return possible
