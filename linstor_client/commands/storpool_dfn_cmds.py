import linstor_client.argparse.argparse as argparse

import linstor
from linstor import SizeCalc
import linstor_client
from ..utils import Output, Color
from linstor_client.commands import Commands
from linstor.sharedconsts import KEY_STOR_POOL_DFN_MAX_OVERSUBSCRIPTION_RATIO


class StoragePoolDefinitionCommands(Commands):
    def __init__(self):
        super(StoragePoolDefinitionCommands, self).__init__()

    def setup_commands(self, parser):
        # storpool subcommands
        subcmds = [
            Commands.Subcommands.Create,
            Commands.Subcommands.List,
            Commands.Subcommands.Delete,
            Commands.Subcommands.SetProperty,
            Commands.Subcommands.ListProperties,
            Commands.Subcommands.QueryMaxVlmSize
        ]

        spd_parser = parser.add_parser(
            Commands.STORAGE_POOL_DEF,
            aliases=["spd"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Storage pool definition subcommands")
        spd_subp = spd_parser.add_subparsers(
            title="Storage pool definition subcommands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmds)
        )

        # new-storpol definition
        p_new_storpool_dfn = spd_subp.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            description='Defines a Linstor storpool definition for use with linstor.')
        p_new_storpool_dfn.add_argument(
            'name',
            type=str,
            help='Name of the new storpool definition')
        p_new_storpool_dfn.set_defaults(func=self.create)

        # remove-storpool definition
        p_rm_storpool_dfn = spd_subp.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
            description='Removes a storage pool definition')
        p_rm_storpool_dfn.add_argument('-q', '--quiet', action="store_true",
                                       help='Unless this option is used, linstor will issue a safety question '
                                       'that must be answered with yes, otherwise the operation is canceled.')
        p_rm_storpool_dfn.add_argument(
            'name',
            nargs="+",
            help='Name of the storage pool to delete').completer = self.storage_pool_dfn_completer
        p_rm_storpool_dfn.set_defaults(func=self.delete)

        # list storpool definitions
        p_lstorpooldfs = spd_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Prints a list of all storage pool definitions known to '
            'linstor. By default, the list is printed as a human readable table.')
        p_lstorpooldfs.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lstorpooldfs.set_defaults(func=self.list)

        # show properties
        p_sp = spd_subp.add_parser(
            Commands.Subcommands.ListProperties.LONG,
            aliases=[Commands.Subcommands.ListProperties.SHORT],
            description="Prints all properties of the given storage pool definition.")
        p_sp.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_sp.add_argument(
            'storage_pool_name',
            help="Storage pool definition for which to print the properties"
        ).completer = self.storage_pool_dfn_completer
        p_sp.set_defaults(func=self.print_props)

        # set properties
        p_setprop = spd_subp.add_parser(
            Commands.Subcommands.SetProperty.LONG,
            aliases=[Commands.Subcommands.SetProperty.SHORT],
            formatter_class=argparse.RawTextHelpFormatter,
            description='Sets properties for the given storage pool definition.')
        p_setprop.add_argument(
            'name',
            type=str,
            help='Name of the storage pool definition'
        ).competer = self.storage_pool_dfn_completer
        Commands.add_parser_keyvalue(p_setprop, "storagepool-definition")
        p_setprop.set_defaults(func=self.set_props)

        p_query_max_vlm_size = spd_subp.add_parser(
            Commands.Subcommands.QueryMaxVlmSize.LONG,
            aliases=[Commands.Subcommands.QueryMaxVlmSize.SHORT],
            description='Queries the controller for storage pools maximum volume size.')
        p_query_max_vlm_size.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_query_max_vlm_size.add_argument(
            '--storage-pool', '-s',
            type=str,
            help="Storage pool name to query.").completer = self.storage_pool_dfn_completer
        p_query_max_vlm_size.add_argument(
            '--do-not-place-with',
            type=str,
            nargs='+',
            metavar="RESOURCE_NAME",
            help='Try to avoid nodes that already have a given resource deployed.'
        ).completer = self.resource_completer
        p_query_max_vlm_size.add_argument(
            '--do-not-place-with-regex',
            type=str,
            metavar="RESOURCE_REGEX",
            help='Try to avoid nodes that already have a resource ' +
                 'deployed whos name is matching the given regular expression.'
        )
        p_query_max_vlm_size.add_argument(
            '--replicas-on-same',
            nargs='+',
            default=[],
            metavar="AUX_NODE_PROPERTY",
            help='Tries to place resources on nodes with the same given auxiliary node property values.'
        )
        p_query_max_vlm_size.add_argument(
            '--replicas-on-different',
            nargs='+',
            default=[],
            metavar="AUX_NODE_PROPERTY",
            help='Tries to place resources on nodes with a different value for the given auxiliary node property.'
        )
        p_query_max_vlm_size.add_argument(
            'replica_count',
            type=int,
            metavar="REPLICA_COUNT",
            help='The least amount of replicas.'
        )
        p_query_max_vlm_size.set_defaults(func=self.query_max_volume_size)

        self.check_subcommands(spd_subp, subcmds)

    def create(self, args):
        replies = self._linstor.storage_pool_dfn_create(args.name)
        return self.handle_replies(args, replies)

    def delete(self, args):
        # execute delete storpooldfns and flatten result list
        replies = [x for subx in args.name for x in self._linstor.storage_pool_dfn_delete(subx)]
        return self.handle_replies(args, replies)

    @classmethod
    def show(cls, args, lstmsg):
        tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        tbl.add_column("StoragePool")
        for storpool_dfn in lstmsg.storage_pool_definitions:
            tbl.add_row([
                storpool_dfn.name
            ])
        tbl.show()

    def list(self, args):
        lstmsg = self._linstor.storage_pool_dfn_list()
        return self.output_list(args, lstmsg, self.show)

    @classmethod
    def _props_show(cls, args, lstmsg):
        result = []
        if lstmsg:
            for storpool_dfn in lstmsg.storage_pool_definitions:
                result.append(storpool_dfn.properties)
        return result

    def print_props(self, args):
        lstmsg = self._linstor.storage_pool_dfn_list()
        return self.output_props_list(args, lstmsg, self._props_show)

    def set_props(self, args):
        args = self._attach_aux_prop(args)
        mod_prop_dict = Commands.parse_key_value_pairs([args.key + '=' + args.value])
        replies = self._linstor.storage_pool_dfn_modify(args.name, mod_prop_dict['pairs'], mod_prop_dict['delete'])
        return self.handle_replies(args, replies)

    def _show_query_max_volume(self, args, lstmsg):
        """
        DEPRECATED will be removed
        :param args:
        :param lstmsg:
        :return:
        """
        print(
            Output.color_str("DEPRECATED:", Color.YELLOW, args.no_color) +
            " use `linstor controller query-max-volume-size`"
        )
        tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        tbl.add_column("StoragePool")
        tbl.add_column("MaxVolumeSize", just_txt='>')
        tbl.add_column("Provisioning")
        tbl.add_column("Nodes")

        def limited_string(obj_list):
            limit = 40
            s = ""
            list_length = len(obj_list)
            for i in range(0, len(obj_list)):
                obj = obj_list[i]
                s += obj + (", " if i != list_length - 1 else "")
                if len(s) > limit:
                    s = s[:limit-3] + "..."

            return s

        storage_pool_dfns = self.get_linstorapi().storage_pool_dfn_list()[0].storage_pool_definitions

        for candidate in lstmsg.candidates:
            max_vlm_size = SizeCalc.approximate_size_string(candidate.max_volume_size)

            storage_pool_props = [x for x in storage_pool_dfns if x.name == candidate.storage_pool][0].properties
            max_oversubscription_ratio_props = \
                [x for x in storage_pool_props if x.key == KEY_STOR_POOL_DFN_MAX_OVERSUBSCRIPTION_RATIO]
            max_oversubscription_ratio_prop = max_oversubscription_ratio_props[0].value \
                if max_oversubscription_ratio_props \
                else lstmsg.default_max_oversubscription_ratio
            max_oversubscription_ratio = float(max_oversubscription_ratio_prop)

            tbl.add_row([
                candidate.storage_pool,
                max_vlm_size,
                "Thin, oversubscription ratio " + str(max_oversubscription_ratio) if candidate.all_thin else "Thick",
                limited_string(candidate.node_names)
            ])
        tbl.show()

    def query_max_volume_size(self, args):
        replies = self.get_linstorapi().storage_pool_dfn_max_vlm_sizes(
            args.replica_count,
            args.storage_pool,
            args.do_not_place_with,
            args.do_not_place_with_regex,
            [linstor.consts.NAMESPC_AUXILIARY + '/' + x for x in args.replicas_on_same],
            [linstor.consts.NAMESPC_AUXILIARY + '/' + x for x in args.replicas_on_different]
        )

        api_responses = self.get_linstorapi().filter_api_call_response(replies)
        if api_responses:
            return self.handle_replies(args, api_responses)

        return self.output_list(args, replies, self._show_query_max_volume)
