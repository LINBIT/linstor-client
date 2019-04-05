GIT = git
INSTALLFILES=.installfiles
PYTHON = python2
LINSTORAPI = ../linstor-api-py
override GITHEAD := $(shell test -e .git && $(GIT) rev-parse HEAD)

U := $(shell $(PYTHON) ./setup.py versionup2date >/dev/null 2>&1; echo $$?;)
TESTS = $(wildcard unit-tests/*_test.py)
DOCKERREGISTRY = drbd.io
DOCKERREGISTRY_QUAY = quay.io
DOCKERREGPATH = $(DOCKERREGISTRY)/linstor-client
DOCKERREGPATH_QUAY = $(DOCKERREGISTRY_QUAY)/linbit/linstor-client
DOCKERREGPATH_DOCKER = linbit/linstor-client
DOCKER_TAG ?= latest

all: doc
	$(PYTHON) setup.py build

doc:
	PYTHONPATH=$(LINSTORAPI):. $(PYTHON) setup.py build_man

install: linstor_client/consts_githash.py
	$(PYTHON) setup.py install --record $(INSTALLFILES)

uninstall:
	test -f $(INSTALLFILES) && cat $(INSTALLFILES) | xargs rm -rf || true
	rm -f $(INSTALLFILES)

ifneq ($(U),0)
up2date:
	$(error "Update your Version strings/Changelogs")
else
up2date: linstor_client/consts_githash.py
	$(info "Version strings/Changelogs up to date")
endif

release: up2date clean doc
	$(PYTHON) setup.py sdist
	@echo && echo "Did you run distclean?"
	@echo && echo "Did you generate and commit the latest drbdsetup options?"

debrelease:
	echo 'recursive-include debian *' >> MANIFEST.in
	dh_clean || true
	make release
	git checkout MANIFEST.in

ifneq ($(FORCE),1)
dockerimage: debrelease
	cd $(LINSTORAPI) && make debrelease
	cp $(LINSTORAPI)/dist/*.tar.gz dist/
else
dockerimage:
endif
	docker build -t $(DOCKERREGPATH):$(DOCKER_TAG) .
	docker tag $(DOCKERREGPATH):$(DOCKER_TAG) $(DOCKERREGPATH):latest
	docker tag $(DOCKERREGPATH):$(DOCKER_TAG) $(DOCKERREGPATH_QUAY):$(DOCKER_TAG)
	docker tag $(DOCKERREGPATH_QUAY):$(DOCKER_TAG) $(DOCKERREGPATH_QUAY):latest
	docker tag $(DOCKERREGPATH):$(DOCKER_TAG) $(DOCKERREGPATH_DOCKER):$(DOCKER_TAG)
	docker tag $(DOCKERREGPATH_DOCKER):$(DOCKER_TAG) $(DOCKERREGPATH_DOCKER):latest
	@echo && echo "Did you run distclean?"

.PHONY: dockerpath
dockerpath:
	@echo $(DOCKERREGPATH):latest $(DOCKERREGPATH):$(DOCKER_TAG) \
		$(DOCKERREGPATH_QUAY):latest $(DOCKERREGPATH_QUAY):$(DOCKER_TAG) \
		$(DOCKERREGPATH_DOCKER):latest $(DOCKERREGPATH_DOCKER):$(DOCKER_TAG)

# no gensrc here, that is in debian/rules
deb: up2date
	[ -d ./debian ] || (echo "Your checkout/tarball does not contain a debian directory" && false)
	debuild -i -us -uc -b

# it is up to you (or the buildenv) to provide a distri specific setup.cfg
rpm: up2date
	$(PYTHON) setup.py bdist_rpm

.PHONY: linstor_client/consts_githash.py
ifdef GITHEAD
override GITDIFF := $(shell $(GIT) diff --name-only HEAD 2>/dev/null | \
			grep -vxF "MANIFEST.in" | \
			tr -s '\t\n' '  ' | \
			sed -e 's/^/ /;s/ *$$//')
linstor_client/consts_githash.py:
	@echo "GITHASH = 'GIT-hash: $(GITHEAD)$(GITDIFF)'" > $@
else
linstor_client/consts_githash.py:
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
