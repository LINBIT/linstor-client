from __future__ import print_function

import linstor_client
import linstor_client.argparse.argparse as argparse
from linstor_client.commands import Commands


class KeyValueStoreCommands(Commands):
    _kv_list_headers = [
        linstor_client.TableHeader("Name"),
    ]

    _kv_show_headers = [
        linstor_client.TableHeader("Key"),
        linstor_client.TableHeader("Value"),
    ]

    def __init__(self):
        super(KeyValueStoreCommands, self).__init__()

    def instance_completer(self, prefix, **kwargs):
        lapi = self.get_linstorapi(**kwargs)
        possible = set()

        instances = lapi.keyvaluestores().instances()
        if instances:
            possible = set(instances)

            if prefix:
                return {instance for instance in possible if instance.startswith(prefix)}

        return possible

    def key_completer(self, prefix, **kwargs):
        lapi = self.get_linstorapi(**kwargs)
        instance = kwargs['parsed_args'].instance
        possible = set()

        lst = lapi.keyvaluestore_list(instance)
        if lst:
            possible = set(lst.properties.keys())

            if prefix:
                return {key for key in possible if key.startswith(prefix)}

        return possible

    def setup_commands(self, parser):
        subcommands = [
            Commands.Subcommands.List,
            Commands.Subcommands.Show,
            Commands.Subcommands.Modify,
        ]

        kv_parser = parser.add_parser(
            Commands.KEY_VALUE_STORE,
            aliases=["kv"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Key-value store subcommands")
        kv_subp = kv_parser.add_subparsers(
            title="key-value store commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcommands)
        )

        p_kv_list = kv_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Lists all key-value store instances.')
        p_kv_list.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_kv_list.set_defaults(func=self.list)

        p_kv_show = kv_subp.add_parser(
            Commands.Subcommands.Show.LONG,
            aliases=[Commands.Subcommands.Show.SHORT],
            description='Lists all key-value pairs in a key-value store instance.')
        p_kv_show.add_argument(
            'instance',
            type=str,
            help='Key-value store instance to operate on').completer = self.instance_completer
        p_kv_show.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output.')
        p_kv_show.set_defaults(func=self.show)

        p_kv_modify = kv_subp.add_parser(
            Commands.Subcommands.Modify.LONG,
            aliases=[Commands.Subcommands.Modify.SHORT],
            description='Modify the value for a given key in the key-value store.')
        p_kv_modify.add_argument(
            'instance',
            type=str,
            help='Key-value store instance to operate on').completer = self.instance_completer
        p_kv_modify.add_argument(
            'key',
            type=str,
            help='Key to modify').completer = self.key_completer
        p_kv_modify.add_argument(
            'value',
            nargs='?',
            type=str,
            help='Value to set key to')
        p_kv_modify.set_defaults(func=self.modify)

        self.check_subcommands(kv_subp, subcommands)

    def list(self, args):
        list_message = self._linstor.keyvaluestores()
        return self.output_list(args, list_message.instances(), self.table_list, single_item=False)

    def show(self, args):
        list_message = self._linstor.keyvaluestore_list(args.instance)
        items = list(list_message.properties.items())
        return self.output_list(args, items, self.table_show, single_item=False)

    def modify(self, args):
        mod_prop_dict = Commands.parse_key_value_pairs([(args.key, args.value)])
        replies = self._linstor.keyvaluestore_modify(
            args.instance,
            property_dict=mod_prop_dict['pairs'],
            delete_props=mod_prop_dict['delete']
        )
        self.handle_replies(args, replies)

    @staticmethod
    def table_list(args, lstmsg):
        tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        for hdr in KeyValueStoreCommands._kv_list_headers:
            tbl.add_header(hdr)

        for name in lstmsg:
            tbl.add_row([name])

        tbl.show()

    @staticmethod
    def table_show(args, lstmsg):
        tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        for hdr in KeyValueStoreCommands._kv_show_headers:
            tbl.add_header(hdr)

        for key, value in lstmsg:
            tbl.add_row([key, value])

        tbl.show()
