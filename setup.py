#!/usr/bin/env python3
"""
    linstor - management of distributed DRBD9 resources
    Copyright (C) 2013 - 2017  LINBIT HA-Solutions GmbH
    Author: Robert Altnoeder, Philipp Reisner

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import glob
import sys

from setuptools import setup, Command


def get_version():
    main_ns = {}
    with open("linstor_client/consts.py") as ver_file:
        exec(ver_file.read(), main_ns)
    return main_ns['VERSION']


class BuildManCommand(Command):
    """
    Builds manual pages using docbook
    """

    description = "Build manual pages"
    user_options = []

    def initialize_options(self):
        self.cwd = None

    def finalize_options(self):
        self.cwd = os.getcwd()

    def run(self):
        assert os.getcwd() == self.cwd, "Must be in package root: %s" % self.cwd
        from linstor_client_main import LinStorCLI
        outdir = "man-pages"
        name = "linstor"
        mansection = '8'
        client = LinStorCLI()
        # use the public property; _all_commands is lazily populated since
        # lazy subparser registration (commit a4ccfbf) was introduced.
        all_commands = client.all_commands
        descriptions = client.parser_cmds_description(all_commands)

        if not os.path.isfile(os.path.join(outdir, "linstor.8.gz")):
            h = open(os.path.join(outdir, "linstor_header.xml"))
            t = open(os.path.join(outdir, "linstor_trailer.xml"))
            linstorxml = open(os.path.join(outdir, "linstor.xml"), 'w')
            linstorxml.write(h.read())
            for cmd in [cmds[0] for cmds in all_commands]:
                linstorxml.write("""
                <varlistentry>
                  <term>
                      <command moreinfo="none">linstor</command>
                      <arg choice="plain" rep="norepeat">%s
                      </arg>
                  </term>
                  <listitem>
                    <para>
                       %s
                    </para>
                    <para>For furter information see
                        <citerefentry>
                        <refentrytitle>%s</refentrytitle>
                        <manvolnum>%s</manvolnum></citerefentry>
                    </para>
                  </listitem>
                </varlistentry>
                """ % (cmd, descriptions[cmd], name + '-' + cmd, mansection))
            linstorxml.write(t.read())
            h.close()
            t.close()
            linstorxml.close()

            os.system("cd %s; " % outdir
                      + " xsltproc --xinclude --stringparam variablelist.term.break.after 1 "
                      "http://docbook.sourceforge.net/release/xsl/current/manpages/docbook.xsl "
                      "linstor.xml; gzip -f -9 linstor.8")
        # subcommands
        import gzip
        if "__enter__" not in dir(gzip.GzipFile):  # duck punch it in!
            def __enter(self):
                if self.fileobj is None:
                    raise ValueError("I/O operation on closed GzipFile object")
                return self

            def __exit(self, *args):
                self.close()

            gzip.GzipFile.__enter__ = __enter
            gzip.GzipFile.__exit__ = __exit

        from linstor_client.utils import check_output

        replace = ("linstor_client_main.py", "linstor")

        for cmd in all_commands:
            toplevel = cmd[0]
            # aliases = cmd[1:]
            # we could use the aliases to symlink them to the toplevel cmd
            outfile = os.path.join('.', outdir, name + '-' + toplevel + '.' + mansection + ".gz")
            if os.path.isfile(outfile):
                continue
            sys.stdout.write("Generating %s ...\n" % (outfile))
            mangen = ["help2man", "-n", toplevel, '-s', mansection,
                      '--version-string=%s' % (get_version()), "-N",
                      '"./linstor_client_main.py %s"' % (toplevel)]

            toexec = " ".join(mangen)
            manpage = check_output(toexec, shell=True).decode()
            manpage = manpage.replace(replace[0], replace[1])
            manpage = manpage.replace(replace[0].upper(), replace[1].upper())
            manpage = manpage.replace(toplevel.upper(), mansection)
            manpage = manpage.replace("%s %s" % (replace[1], toplevel),
                                      "%s_%s" % (replace[1], toplevel))
            with gzip.open(outfile, 'wb') as f:
                f.write(manpage.encode())


def gen_data_files():
    data_files = []
    for manpage in glob.glob(os.path.join("man-pages", "*.8.gz")):
        data_files.append(("/usr/share/man/man8", [manpage]))
    return data_files


setup(
    name="linstor-client",
    version=get_version(),
    description="DRBD distributed resource management utility",
    long_description="This client program communicates to controller node which manages the resources",
    author="Robert Altnoeder <robert.altnoeder@linbit.com>, Roland Kammerer <roland.kammerer@linbit.com>"
           + ", Rene Peinthor <rene.peinthor@linbit.com>",
    author_email="roland.kammerer@linbit.com",
    maintainer="LINBIT HA-Solutions GmbH",
    maintainer_email="drbd-dev@lists.linux.dev",
    url="https://www.linbit.com",
    license="GPLv3",
    python_requires=">=3.6",
    packages=[
        "linstor_client",
        "linstor_client.commands",
        "linstor_client.commands.utils",
    ],
    install_requires=[
        "python-linstor>=1.28.0",
        "argcomplete>=1.8.1",
    ],
    py_modules=["linstor_client_main"],
    scripts=["scripts/linstor"],
    data_files=gen_data_files(),
    cmdclass={
        "build_man": BuildManCommand,
    },
    test_suite="tests.test_without_controller"
)
