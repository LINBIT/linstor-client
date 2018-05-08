import linstor.argparse.argparse as argparse
from linstor.commands import Commands, DrbdOptions


class ControllerCommands(Commands):
    def __init__(self):
        super(ControllerCommands, self).__init__()

    def setup_commands(self, parser):
        # Controller commands
        subcmds = [
            Commands.Subcommands.SetProperty,
            Commands.Subcommands.ListProperties,
            Commands.Subcommands.Shutdown,
            Commands.Subcommands.DrbdOptions
        ]

        con_parser = parser.add_parser(
            Commands.CONTROLLER,
            aliases=["c"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Controller subcommands")

        con_subp = con_parser.add_subparsers(
            title="Controller commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmds)
        )

        # Controller - get props
        c_ctrl_props = con_subp.add_parser(
            Commands.Subcommands.ListProperties.LONG,
            aliases=[Commands.Subcommands.ListProperties.SHORT],
            description='Print current controller config properties.')
        c_ctrl_props.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        c_ctrl_props.set_defaults(func=self.cmd_print_controller_props)

        #  controller - set props
        c_set_ctrl_props = con_subp.add_parser(
            Commands.Subcommands.SetProperty.LONG,
            aliases=[Commands.Subcommands.SetProperty.SHORT],
            description='Set a controller config property.')
        Commands.add_parser_keyvalue(c_set_ctrl_props, "controller")
        c_set_ctrl_props.set_defaults(func=self.set_props)

        c_drbd_opts = con_subp.add_parser(
            Commands.Subcommands.DrbdOptions.LONG,
            aliases=[Commands.Subcommands.DrbdOptions.SHORT],
            description="Set common drbd options."
        )
        DrbdOptions.add_arguments(c_drbd_opts, DrbdOptions.drbd_options()['options'].keys())
        c_drbd_opts.set_defaults(func=self.cmd_controller_drbd_opts)

        # Controller - shutdown
        c_shutdown = con_subp.add_parser(
            Commands.Subcommands.Shutdown.LONG,
            aliases=[Commands.Subcommands.Shutdown.SHORT],
            description='Shutdown the linstor controller'
        )
        c_shutdown.set_defaults(func=self.cmd_shutdown)

        self.check_subcommands(con_subp, subcmds)

    @classmethod
    def _props_list(cls, args, lstmsg):
        result = []
        if lstmsg:
            result.append(lstmsg.props)
        return result

    def cmd_print_controller_props(self, args):
        lstmsg = self._linstor.controller_props()

        return self.output_props_list(args, lstmsg, self._props_list)

    def set_props(self, args):
        props = Commands.parse_key_value_pairs([args.key + '=' + args.value])

        replies = [x for subx in props['pairs'] for x in self._linstor.controller_set_prop(subx, props['pairs'][subx])]
        return self.handle_replies(args, replies)

    def cmd_controller_drbd_opts(self, args):
        a = DrbdOptions.filter_new(args)

        mod_props, del_props = DrbdOptions.parse_opts(a)

        replies = []
        for prop, val in mod_props.items():
            replies.extend(self._linstor.controller_set_prop(prop, val))

        for delkey in del_props:
            replies.extend(self._linstor.controller_del_prop(delkey))

        return self.handle_replies(args, replies)

    def cmd_shutdown(self, args):
        replies = self._linstor.shutdown_controller()
        return self.handle_replies(args, replies)