from __future__ import print_function

import getpass

import linstor_client.argparse.argparse as argparse
from linstor_client.commands import Commands
from linstor_client import Table


class RemoteCommands(Commands):

    class SubCmdS3(object):
        LONG = "s3"
        SHORT = "s3"

    class SubCmdLinstor(object):
        LONG = "linstor"
        SHORT = "l"

    class SubCmdEbs(object):
        LONG = "ebs"
        SHORT = "ebs"

    def setup_commands(self, parser):
        subcmds = [
            Commands.Subcommands.List,
            Commands.Subcommands.Create,
            Commands.Subcommands.Modify,
            Commands.Subcommands.Delete,
        ]

        create_modify_subcmds = [
            RemoteCommands.SubCmdS3,
            RemoteCommands.SubCmdLinstor,
            RemoteCommands.SubCmdEbs
        ]

        rmo_parser = parser.add_parser(
            Commands.REMOTE,
            formatter_class=argparse.RawTextHelpFormatter,
            description="Remote subcommands")
        rmo_sub = rmo_parser.add_subparsers(
            title="remote commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmds)
        )

        # list
        p_lremotes = rmo_sub.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Prints a list of all remotes.'
        )
        p_lremotes.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lremotes.set_defaults(func=self.list_remotes)

        # create
        p_crt_remote = rmo_sub.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Create a new remote."
        )
        p_crt_sub = p_crt_remote.add_subparsers(
            title="remote create commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(create_modify_subcmds)
        )

        # create s3
        p_crt_s3_remote = p_crt_sub.add_parser(
            RemoteCommands.SubCmdS3.LONG,
            aliases=[RemoteCommands.SubCmdS3.SHORT],
            description="Create a new S3 remote"
        )
        p_crt_s3_remote.add_argument("--use-path-style", action="store_true", default=False,
                                     help="Set if you AWS instance uses path style")
        p_crt_s3_remote.add_argument("name", help="Remote name")
        p_crt_s3_remote.add_argument("endpoint", help="Endpoint of the S3 remote")
        p_crt_s3_remote.add_argument("bucket", help="Bucket of the S3 remote")
        p_crt_s3_remote.add_argument("region", help="Region of the S3 remote")
        p_crt_s3_remote.add_argument("access_key", help="Access key of the S3 remote")
        p_crt_s3_remote.add_argument("secret_key", nargs="?",
                                     help="Secret key of the S3 remote, if not provided will be prompted")
        p_crt_s3_remote.set_defaults(func=self.create_s3)

        # create linstor
        p_crt_linstor_remote = p_crt_sub.add_parser(
            RemoteCommands.SubCmdLinstor.LONG,
            aliases=[RemoteCommands.SubCmdLinstor.SHORT],
            description="Create a new Linstor remote")
        p_crt_linstor_remote.add_argument("name", help="Remote name")
        p_crt_linstor_remote.add_argument("url", help="URL of the target Linstor controller")
        p_crt_linstor_remote.add_argument(
            "--cluster-id",
            help="UUID of the target Linstor cluster. See 'Cluster/LocalID' property on REMOTE controller level")
        p_crt_linstor_remote.add_argument(
            "--passphrase",
            type=str,
            nargs='?',
            action='store',
            help="Passphrase of the target Linstor controller (needed if shipping LUKS based backups)",
            const='')
        p_crt_linstor_remote.set_defaults(func=self.create_linstor)

        # create ebs
        p_crt_ebs_remote = p_crt_sub.add_parser(
            RemoteCommands.SubCmdEbs.LONG,
            aliases=[RemoteCommands.SubCmdEbs.SHORT],
            description="Create a new EBS remote"
        )
        p_crt_ebs_remote.add_argument("name", help="Remote name")
        p_crt_ebs_remote.add_argument("availability_zone", help="Availability zone. Example: eu-central-1b")
        p_crt_ebs_remote.add_argument(
            "--endpoint",
            help="Endpoint of the EBS remote. If omitted the endpoint is constructed based on the region")
        p_crt_ebs_remote.add_argument(
            "--region", help="Region of the EBS remote. If omitted the region is constructed based on the availability \
            zone")
        p_crt_ebs_remote.add_argument("access_key", help="Access key of the EBS remote")
        p_crt_ebs_remote.add_argument("secret_key", nargs="?",
                                      help="Secret key of the EBS remote, if not provided will be prompted")
        p_crt_ebs_remote.set_defaults(func=self.create_ebs)

        # modify
        p_mod_remote = rmo_sub.add_parser(
            Commands.Subcommands.Modify.LONG,
            aliases=[Commands.Subcommands.Modify.SHORT],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Modify a remote."
        )
        p_mod_sub = p_mod_remote.add_subparsers(
            title="remote modify commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(create_modify_subcmds)
        )

        # modify s3
        p_mod_s3 = p_mod_sub.add_parser(
            RemoteCommands.SubCmdS3.LONG,
            aliases=[RemoteCommands.SubCmdS3.SHORT],
            description="Modify a S3 remote"
        )
        p_mod_s3.add_argument("name", help="Remote name").completer = self.remote_completer
        p_mod_s3.add_argument("--endpoint", help="Endpoint of the S3 remote")
        p_mod_s3.add_argument("--bucket", help="Bucket of the S3 remote")
        p_mod_s3.add_argument("--region", help="Region of the S3 remote")
        p_mod_s3.add_argument("--access_key", help="Access key of the S3 remote")
        p_mod_s3.add_argument("--secret_key",
                              nargs="?",
                              action='store',
                              const='',
                              help="Secret key of the S3 remote, if not provided will be prompted")
        p_mod_s3.set_defaults(func=self.modify_s3)

        # modify linstor
        p_mod_linstor_remote = p_mod_sub.add_parser(
            RemoteCommands.SubCmdLinstor.LONG,
            aliases=[RemoteCommands.SubCmdLinstor.SHORT],
            description="Modify a Linstor remote")
        p_mod_linstor_remote.add_argument("name", help="Remote name").completer = self.remote_completer
        p_mod_linstor_remote.add_argument("--url", help="URL of the target Linstor controller")
        p_mod_linstor_remote.add_argument(
            "--cluster-id",
            help="UUID of the target Linstor cluster. See 'Cluster/LocalID' property on REMOTE controller level")
        p_mod_linstor_remote.add_argument(
            "--passphrase",
            type=str,
            nargs='?',
            action='store',
            help="Passphrase of the target Linstor controller (needed if shipping LUKS based backups)",
            const='')
        p_mod_linstor_remote.set_defaults(func=self.modify_linstor)

        # modify ebs
        p_mod_ebs = p_mod_sub.add_parser(
            RemoteCommands.SubCmdEbs.LONG,
            aliases=[RemoteCommands.SubCmdEbs.SHORT],
            description="Modify a EBS remote"
        )
        p_mod_ebs.add_argument("name", help="Remote name").completer = self.remote_completer
        p_mod_ebs.add_argument("--endpoint", help="Endpoint of the EBS remote")
        p_mod_ebs.add_argument("--availability-zone", "--az",
                               help="Availability Zone of the EBS remote. Example: eu-central-1b")
        p_mod_ebs.add_argument("--region", help="Region of the EBS remote")
        p_mod_ebs.add_argument("--access_key", help="Access key of the EBS remote")
        p_mod_ebs.add_argument("--secret_key",
                               nargs="?",
                               action='store',
                               const='',
                               help="Secret key of the EBS remote, if not provided will be prompted")
        p_mod_ebs.set_defaults(func=self.modify_ebs)

        # delete
        p_del_remote = rmo_sub.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
            description="Delete a remote."
        )
        p_del_remote.add_argument("name").completer = self.remote_completer
        p_del_remote.set_defaults(func=self.delete)

        self.check_subcommands(p_crt_sub, create_modify_subcmds)
        self.check_subcommands(p_mod_sub, create_modify_subcmds)
        self.check_subcommands(rmo_sub, subcmds)

    @staticmethod
    def show_remotes(args, remotes):
        """

        :param args:
        :param linstor.responses.RemoteListResponse remotes:
        :return:
        """
        tbl = Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        tbl.add_column("Name")
        tbl.add_column("Type")
        tbl.add_column("Info")

        rows = []
        for s3 in remotes.s3_remotes:
            rows.append({
                "name": s3.remote_name,
                "type": "S3",
                "info": "{r}.{e}/{b}".format(r=s3.region, e=s3.endpoint, b=s3.bucket)})
        for lin_remote in remotes.linstor_remotes:
            rows.append({
                "name": lin_remote.remote_name,
                "type": "Linstor",
                "info": lin_remote.url
            })
        for ebs in remotes.ebs_remotes:
            rows.append({
                "name": ebs.remote_name,
                "type": "EBS",
                "info": "{url}, AZ: {az}".format(url=ebs.endpoint, az=ebs.availability_zone)
            })
        for remote in rows:
            tbl.add_row([remote["name"], remote["type"], remote["info"]])
        tbl.show()

    def list_remotes(self, args):
        lstmsg = self.get_linstorapi().remote_list()
        return self.output_list(
            args,
            lstmsg,
            RemoteCommands.show_remotes,
            machine_readable_raw=True)

    def create_s3(self, args):
        if args.secret_key:
            password = args.secret_key
        else:
            password = getpass.getpass("Secret-key: ")  # read from keyboard
        replies = self.get_linstorapi().remote_create_s3(
            remote_name=args.name,
            endpoint=args.endpoint,
            region=args.region,
            bucket=args.bucket,
            access_key=args.access_key,
            secret_key=password,
            use_path_style=args.use_path_style)
        return self.handle_replies(args, replies)

    def modify_s3(self, args):
        password = None
        if args.secret_key is not None:
            if args.secret_key:
                password = args.secret_key
            else:
                password = getpass.getpass("Secret-key: ")  # read from keyboard
        replies = self.get_linstorapi().remote_modify_s3(
            remote_name=args.name,
            endpoint=args.endpoint,
            region=args.region,
            bucket=args.bucket,
            access_key=args.access_key,
            secret_key=password)
        return self.handle_replies(args, replies)

    def create_linstor(self, args):
        passphrase = None
        if args.passphrase is not None:
            if args.passphrase:
                passphrase = args.passphrase
            else:
                passphrase = getpass.getpass("Remote controllers passphrase: ")  # read from keyboard
        replies = self.get_linstorapi().remote_create_linstor(
            remote_name=args.name,
            url=args.url,
            passphrase=passphrase,
            cluster_id=args.cluster_id)
        return self.handle_replies(args, replies)

    def modify_linstor(self, args):
        passphrase = None
        if args.passphrase is not None:
            if args.passphrase:
                passphrase = args.passphrase
            else:
                passphrase = getpass.getpass("Remote controllers passphrase: ")  # read from keyboard
        replies = self.get_linstorapi().remote_modify_linstor(
            remote_name=args.name,
            url=args.url,
            passphrase=passphrase,
            cluster_id=args.cluster_id)
        return self.handle_replies(args, replies)

    def create_ebs(self, args):
        if args.secret_key:
            password = args.secret_key
        else:
            password = getpass.getpass("Secret-key: ")  # read from keyboard
        replies = self.get_linstorapi().remote_create_ebs(
            remote_name=args.name,
            availability_zone=args.availability_zone,
            endpoint=args.endpoint,
            region=args.region,
            access_key=args.access_key,
            secret_key=password)
        return self.handle_replies(args, replies)

    def modify_ebs(self, args):
        password = None
        if args.secret_key is not None:
            if args.secret_key:
                password = args.secret_key
            else:
                password = getpass.getpass("Secret-key: ")  # read from keyboard
        replies = self.get_linstorapi().remote_modify_ebs(
            remote_name=args.name,
            endpoint=args.endpoint,
            region=args.region,
            availability_zone=args.availability_zone,
            access_key=args.access_key,
            secret_key=password)
        return self.handle_replies(args, replies)

    def delete(self, args):
        replies = self.get_linstorapi().remote_delete(args.name)
        return self.handle_replies(args, replies)
