import unittest
import linstor_client
import sys
from cStringIO import StringIO
import json
import os
import tarfile
import subprocess
import shutil


db_xml = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
 <!DOCTYPE properties SYSTEM "http://java.sun.com/dtd/properties.dtd">
 <properties>
     <comment>LinStor database configuration</comment>
     <entry key="user">linstor</entry>
     <entry key="password">linstor</entry>
     <entry key="connection-url">jdbc:derby:{path};create=true</entry>
 </properties>
 """

controller_port = 63376

update_port_sql = """
UPDATE PROPS_CONTAINERS SET PROP_VALUE='{port}'
    WHERE PROPS_INSTANCE='CTRLCFG' AND PROP_KEY='netcom/PlainConnector/port';
""".format(port=controller_port)


class LinstorTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        install_path = '/tmp/_linstor'
        linstor_dir = os.path.abspath('../linstor')
        if not os.path.exists(linstor_dir):
            raise RuntimeError("linstor repository not found in: " + linstor_dir)
        linstor_distri_tar = os.path.join(linstor_dir, 'build', 'distributions', 'linstor-1.0.tar')
        try:
            os.removedirs(install_path)
        except OSError:
            pass
        tar = tarfile.open(linstor_distri_tar)
        tar.extractall(install_path)

        database_cfg_path = os.path.join(install_path, 'database.cfg')
        init_sql_path = os.path.join(linstor_dir, 'sql-src', 'drbd-init-derby.sql')
        execute_init_sql_path = os.path.join(install_path, 'init.sql')

        with open(database_cfg_path, 'wt') as databasecfg:
            databasecfg.write(db_xml.format(path=os.path.join(install_path, 'linstor_db')))
        shutil.copyfile(init_sql_path, execute_init_sql_path)
        with open(execute_init_sql_path, 'at') as init_sql_file:
            init_sql_file.write(update_port_sql)

        linstor_bin = os.path.join(install_path, 'linstor-1.0', 'bin')
        ret = subprocess.check_call(
            [
                os.path.join(linstor_bin, 'RecreateDb'),
                database_cfg_path,
                execute_init_sql_path
            ])
        if ret != 0:
            raise RuntimeError("Couldn't execute RecreateDb script")

        # start linstor controller
        cls.controller = subprocess.Popen(
            [os.path.join(linstor_bin, 'linstor')],
            cwd=install_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print('Waiting for controller to start, if this takes longer than 10s cancel')
        while True:
            line = cls.controller.stderr.readline()  # this will block
            if 'Controller initialized' in line:
                break

    @classmethod
    def tearDownClass(cls):
        cls.controller.terminate()

    @classmethod
    def add_controller_arg(cls, cmd_args):
        cmd_args.insert(0, '--controllers')
        cmd_args.insert(1, 'localhost:' + str(controller_port))

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

    def execute_with_maschine_output(self, cmd_args):
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
            retcode = linstor_cli.parse_and_execute(cmd_args + ["-m"])
        except SystemExit as e:
            retcode = e.code
        finally:
            self.assertEqual(retcode, 0)
            jout = json.loads(sys.stdout.getvalue())
            sys.stdout.close()
            sys.stdout = backupstd
        return jout

    def assertHasProp(self, props, key, val):
        for prop in props:
            if prop['key'] == key and prop['value'] == val:
                return True
        raise AssertionError("Prop {prop} with value {val} not in container.".format(prop=key, val=val))
