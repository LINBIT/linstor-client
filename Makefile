GIT = git
INSTALLFILES=.installfiles
PYTHON = python2
override GITHEAD := $(shell test -e .git && $(GIT) rev-parse HEAD)

U := $(shell $(PYTHON) ./setup.py versionup2date >/dev/null 2>&1; echo $$?;)
TESTS = $(wildcard unit-tests/*_test.py)
DOCKERREGISTRY = drbd.io

all: doc
	$(PYTHON) setup.py build

doc: gensrc
	$(PYTHON) setup.py build_man

install: linstor/consts_githash.py
	$(PYTHON) setup.py install --record $(INSTALLFILES)

uninstall:
	test -f $(INSTALLFILES) && cat $(INSTALLFILES) | xargs rm -rf || true
	rm -f $(INSTALLFILES)

ifneq ($(U),0)
up2date:
	$(error "Update your Version strings/Changelogs")
else
up2date: linstor/consts_githash.py
	$(info "Version strings/Changelogs up to date")
endif

.PHONY: linstor/drbdsetup_options.py
linstor/drbdsetup_options.py:
	linstor-common/gendrbdoptions.py python $@

xml: linstor/drbdsetup_options.py

release: up2date clean doc xml
	$(PYTHON) setup.py sdist
	git checkout linstor/drbdsetup_options.py
	@echo && echo "Did you run distclean?"
	@echo && echo "Did you generate and commit the latest drbdsetup options?"

debrelease:
	echo 'recursive-include debian *' >> MANIFEST.in
	dh_clean || true
	make release
	git checkout MANIFEST.in

dockerimage: debrelease
	docker build -t $(DOCKERREGISTRY)/linstor-client .
	@echo && echo "Did you run distclean?"

.PHONY: gensrc
gensrc:
	make -C linstor-common cleanpython
	make -C linstor-common python

# no gensrc here, that is in debian/rules
deb: up2date
	[ -d ./debian ] || (echo "Your checkout/tarball does not contain a debian directory" && false)
	debuild -i -us -uc -b

# it is up to you (or the buildenv) to provide a distri specific setup.cfg
rpm: up2date gensrc
	$(PYTHON) setup.py bdist_rpm

.PHONY: linstor/consts_githash.py
ifdef GITHEAD
override GITDIFF := $(shell $(GIT) diff --name-only HEAD 2>/dev/null | \
			grep -vxF "MANIFEST.in" | \
			tr -s '\t\n' '  ' | \
			sed -e 's/^/ /;s/ *$$//')
linstor/consts_githash.py:
	@echo "GITHASH = 'GIT-hash: $(GITHEAD)$(GITDIFF)'" > $@
else
linstor/consts_githash.py:
	@echo >&2 "Need a git checkout to regenerate $@"; test -s $@
endif

md5sums:
	CURDATE=$$(date +%s); for i in $$(${GIT} ls-files | sort); do md5sum $$i >> md5sums.$${CURDATE}; done

clean:
	$(PYTHON) setup.py clean
	rm -f man-pages/*.gz

distclean: clean
	git clean -d -f || true

check:
	# currently none
	# $(PYTHON) $(TESTS)
