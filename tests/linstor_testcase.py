import unittest
import linstor_client_main
import sys
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
import json
import os
from linstor.linstorapi import ApiCallResponse


controller_port = os.environ.get('LINSTOR_CONTROLLER_PORT', 63370)


class LinstorTestCase(unittest.TestCase):
    @classmethod
    def find_linstor_tar(cls, paths):
        for spath in paths:
            tarpath = os.path.join(spath, "linstor-server.tar")
            if os.path.exists(tarpath):
                return tarpath
        return None

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    @classmethod
    def host(cls):
        return os.environ.get('LINSTOR_CONTROLLER_HOST', 'localhost')

    @classmethod
    def port(cls):
        return controller_port

    @classmethod
    def rest_port(cls):
        return controller_port

    @classmethod
    def signed_mask(cls, mask):
        return mask - 2**64

    @classmethod
    def add_controller_arg(cls, cmd_args):
        cmd_args.insert(0, '--controllers')
        cmd_args.insert(1, cls.host() + ':' + str(cls.rest_port()))

    @classmethod
    def execute(cls, cmd_args):
        LinstorTestCase.add_controller_arg(cmd_args)
        print(cmd_args)
        linstor_cli = linstor_client_main.LinStorCLI()

        try:
            return linstor_cli.parse_and_execute(cmd_args)
        except SystemExit as e:
            print(e)
            return e.code

    @classmethod
    def parse_args(cls, cmd_args):
        LinstorTestCase.add_controller_arg(cmd_args)
        linstor_cli = linstor_client_main.LinStorCLI()

        return linstor_cli.parse(cmd_args)

    def execute_with_machine_output(self, cmd_args):
        """
        Execute the given cmd_args command and adds the machine readable flag.
        Returns the parsed json output.
        """
        LinstorTestCase.add_controller_arg(cmd_args)
        linstor_cli = linstor_client_main.LinStorCLI()
        backupstd = sys.stdout
        jout = None
        try:
            sys.stdout = StringIO()
            retcode = linstor_cli.parse_and_execute(["-m", "--output-version", "v0"] + cmd_args)
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
        linstor_cli = linstor_client_main.LinStorCLI()
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
        """

        :param cmd_args:
        :return:
        :rtype: list[ApiCallResponse]
        """
        d = self.execute_with_machine_output(cmd_args)
        self.assertIsNotNone(d, "No result returned")
        return [ApiCallResponse.from_json(x) for x in d]

    def execute_with_single_resp(self, cmd_args):
        responses = self.execute_with_resp(cmd_args)
        if len(responses) != 1:
            print(responses)
            self.assertEqual(len(responses), 1, "Zero or more than 1 api call responses")
        return responses[0]

    @classmethod
    def assertHasProp(cls, props, key, val):
        for prop in props:
            if prop['key'] == key and prop['value'] == val:
                return True
        raise AssertionError("Prop {prop} with value {val} not in container.".format(prop=key, val=val))

    @classmethod
    def assert_api_succuess(cls, apicall_rc):
        """

        :param ApiCallResponse apicall_rc: apicall rc to check
        :return:
        """
        if not apicall_rc.is_success():
            raise AssertionError("ApiCall no success: " + str(apicall_rc))
        return True

    @classmethod
    def assert_apis_success(cls, apicalls):
        """

        :param list[ApiCallResponse] apicalls:
        :return:
        """
        if not all([not x.is_error() for x in apicalls]):
            raise AssertionError("ApiCall no success: " + str([x for x in apicalls if x.is_error()][0]))
        return True

    def find_prop(self, props, key):
        for prop in props:
            self.assertIn('key', prop)
            if key == prop['key']:
                return prop

        self.assertTrue(False, "Property '{key}' not found.".format(key=key))

    def check_prop(self, prop, key, value):
        self.assertEqual(2, len(prop.keys()))
        self.assertIn('key', prop)
        self.assertIn('value', prop)
        self.assertEqual(key, prop['key'])
        self.assertEqual(value, prop['value'])

    def find_and_check_prop(self, props, key, value):
        prop = self.find_prop(props, key)
        self.check_prop(prop, key, value)
