import unittest
import linstor_client
import sys
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
import json
import os
import tarfile
import subprocess
import zipfile
from linstor.linstorapi import ApiCallResponse


controller_port = 63374 + sys.version_info[0]

update_port_sql = """
UPDATE PROPS_CONTAINERS SET PROP_VALUE='{port}'
    WHERE PROPS_INSTANCE='CTRLCFG' AND PROP_KEY='netcom/PlainConnector/port';
UPDATE PROPS_CONTAINERS SET PROP_VALUE='127.0.0.1'
    WHERE PROPS_INSTANCE='CTRLCFG' AND PROP_KEY='netcom/PlainConnector/bindaddress';
""".format(port=controller_port)


class LinstorTestCase(unittest.TestCase):
    controller = None

    @classmethod
    def find_linstor_tar(cls, paths):
        for spath in paths:
            tarpath = os.path.join(spath, "linstor.tar")
            if os.path.exists(tarpath):
                return tarpath
        return None

    @classmethod
    def setUpClass(cls):
        install_path = os.path.abspath('build/_linstor_unittests')
        linstor_tar_search_paths = [
            os.path.abspath(os.path.join('./')),
            os.path.abspath(os.path.join('../linstor', 'build', 'distributions')),
            os.path.abspath(os.path.join('../linstor-server', 'build', 'distributions'))
        ]
        linstor_distri_tar = cls.find_linstor_tar(linstor_tar_search_paths)

        if linstor_distri_tar is None:
            raise RuntimeError("Unable to find any linstor distribution tar: " + str(linstor_tar_search_paths))

        print("Using " + linstor_distri_tar)
        try:
            os.removedirs(install_path)
        except OSError:
            pass
        with tarfile.open(linstor_distri_tar) as tar:
            tar.extractall(install_path)
            linstor_file_name = tar.getnames()[0]  # on jenkins the tar and folder within is named workspace-1.0

        # get sql init script
        execute_init_sql_path = os.path.join(install_path, 'init.sql')
        linjar_filename = os.path.join(install_path, linstor_file_name, 'lib', linstor_file_name + '.jar')
        with zipfile.ZipFile(linjar_filename, 'r') as linjar:
            with linjar.open('resource/drbd-init-derby.sql', 'r') as sqlfile:
                with open(execute_init_sql_path, 'wt') as init_sql_file:
                    for line in sqlfile:
                        init_sql_file.write(line.decode())
                    # patch init sql file to start controller on different port
                    init_sql_file.write(update_port_sql)

        linstor_bin = os.path.join(install_path, linstor_file_name, 'bin')

        # start linstor controller
        controller_bin = os.path.join(linstor_bin, "Controller")
        print("executing: " + controller_bin)
        cls.controller = subprocess.Popen(
            [controller_bin, "--memory_database", execute_init_sql_path],
            cwd=install_path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print('Waiting for controller to start, if this takes longer than 10s cancel')
        while True:
            line = cls.controller.stderr.readline()  # this will block
            line = line.decode()
            sys.stdout.write(line)
            sys.stdout.flush()
            if 'Controller initialized' in line:
                break

    @classmethod
    def tearDownClass(cls):
        cls.controller.poll()
        if cls.controller.returncode:
            sys.stderr.write("Controller already down!!!.\n")
            raise RuntimeError("Controller already down!!!.")
        cls.controller.terminate()
        cls.controller.wait()
        sys.stdout.write(cls.controller.stdout.read().decode())
        sys.stdout.write(cls.controller.stderr.read().decode())
        cls.controller.stderr.close()
        cls.controller.stdout.close()
        cls.controller.stdin.close()
        sys.stdout.write("Controller terminated.\n")
        sys.stdout.flush()

    @classmethod
    def add_controller_arg(cls, cmd_args):
        cmd_args.insert(0, '--controllers')
        cmd_args.insert(1, '127.0.0.1:' + str(controller_port))

    def execute(self, cmd_args):
        LinstorTestCase.add_controller_arg(cmd_args)
        linstor_cli = linstor_client.LinStorCLI()

        try:
            return linstor_cli.parse_and_execute(cmd_args)
        except SystemExit as e:
            return e.code

    def parse_args(self, cmd_args):
        LinstorTestCase.add_controller_arg(cmd_args)
        linstor_cli = linstor_client.LinStorCLI()

        return linstor_cli.parse(cmd_args)

    def execute_with_machine_output(self, cmd_args):
        """
        Execute the given cmd_args command and adds the machine readable flag.
        Returns the parsed json output.
        """
        LinstorTestCase.add_controller_arg(cmd_args)
        linstor_cli = linstor_client.LinStorCLI()
        backupstd = sys.stdout
        jout = None
        try:
            sys.stdout = StringIO()
            retcode = linstor_cli.parse_and_execute(["-m"] + cmd_args)
            self.assertEqual(0, retcode)
        finally:
            stdval = sys.stdout.getvalue()
            sys.stdout.close()
            sys.stdout = backupstd
            if stdval:
                try:
                    jout = json.loads(stdval)
                except ValueError as ve:
                    sys.stderr.write("Could not parse: {j}\n".format(j=stdval))
                    raise ve
                self.assertIsInstance(jout, list)
            else:
                sys.stderr.write(str(cmd_args) + " Result empty")
        return jout

    def execute_with_text_output(self, cmd_args):
        """
        Execute the given cmd_args command and adds the machine readable flag.
        Returns the parsed json output.
        """
        LinstorTestCase.add_controller_arg(cmd_args)
        linstor_cli = linstor_client.LinStorCLI()
        backupstd = sys.stdout

        try:
            sys.stdout = StringIO()
            retcode = linstor_cli.parse_and_execute(["--no-utf8", "--no-color"] + cmd_args)
            self.assertEqual(0, retcode)
        finally:
            stdval = sys.stdout.getvalue()
            sys.stdout.close()
            sys.stdout = backupstd
        return stdval

    def execute_with_resp(self, cmd_args):
        d = self.execute_with_machine_output(cmd_args)
        self.assertIsNotNone(d, "No result returned")
        return [ApiCallResponse.from_json(x) for x in d]

    def execute_with_single_resp(self, cmd_args):
        responses = self.execute_with_resp(cmd_args)
        self.assertEqual(len(responses), 1, "Zero or more than 1 api call responses")
        return responses[0]

    def assertHasProp(self, props, key, val):
        for prop in props:
            if prop['key'] == key and prop['value'] == val:
                return True
        raise AssertionError("Prop {prop} with value {val} not in container.".format(prop=key, val=val))
