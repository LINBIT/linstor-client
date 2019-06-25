FROM centos:centos7 as builder

ENV LINSTOR_CLI_VERSION 0.9.8
ENV PYTHON_LINSTOR_VERSION 0.9.8

ENV LINSTOR_CLI_PKGNAME linstor-client
ENV LINSTOR_CLI_TGZ ${LINSTOR_CLI_PKGNAME}-${LINSTOR_CLI_VERSION}.tar.gz
ENV PYTHON_LINSTOR_PKGNAME python-linstor
ENV PYTHON_LINSTOR_TGZ ${PYTHON_LINSTOR_PKGNAME}-${PYTHON_LINSTOR_VERSION}.tar.gz

USER root
RUN yum -y update-minimal --security --sec-severity=Important --sec-severity=Critical
RUN groupadd makepkg # !lbbuild
RUN useradd -m -g makepkg makepkg # !lbbuild

RUN yum install -y sudo # !lbbuild
RUN usermod -a -G wheel makepkg # !lbbuild

RUN yum install -y rpm-build python2-setuptools make && yum clean all -y # !lbbuild
RUN rpm -e --nodeps fakesystemd && yum install -y systemd && yum clean all -y || true # !lbbuild

# one can not comment COPY
RUN cd /tmp && curl -sSf https://www.linbit.com/downloads/linstor/$PYTHON_LINSTOR_TGZ > $PYTHON_LINSTOR_TGZ # !lbbuild
RUN cd /tmp && curl -sSf https://www.linbit.com/downloads/linstor/$LINSTOR_CLI_TGZ > $LINSTOR_CLI_TGZ # !lbbuild
# =lbbuild COPY /dist/${PYTHON_LINSTOR_TGZ} /tmp/
# =lbbuild COPY /dist/${LINSTOR_TGZ} /tmp/

USER makepkg
RUN cd ${HOME} && \
		 cp /tmp/${PYTHON_LINSTOR_TGZ} ${HOME} && \
		 tar xvf ${PYTHON_LINSTOR_TGZ} && \
		 cd ${PYTHON_LINSTOR_PKGNAME}-${PYTHON_LINSTOR_VERSION} && \
		 make gensrc && \
		 make rpm && mv ./dist/*.rpm /tmp/
RUN cd ${HOME} && \
		 cp /tmp/${LINSTOR_CLI_TGZ} ${HOME} && \
		 tar xvf ${LINSTOR_CLI_TGZ} && \
		 cd ${LINSTOR_CLI_PKGNAME}-${LINSTOR_CLI_VERSION} && \
		 make rpm && mv ./dist/*.rpm /tmp/

FROM registry.access.redhat.com/ubi7/ubi
MAINTAINER Roland Kammerer <roland.kammerer@linbit.com>

# ENV can not be shared between builder and "main"
ENV LINSTOR_CLI_VERSION 0.9.8
ARG release=1

LABEL name="linstor-client" \
      vendor="LINBIT" \
      version="$LINSTOR_CLI_VERSION" \
      release="$release" \
      summary="LINSTOR's client component" \
      description="LINSTOR's client component"

COPY COPYING /licenses/gpl-3.0.txt

COPY --from=builder /tmp/*.noarch.rpm /tmp/
RUN yum -y update-minimal --security --sec-severity=Important --sec-severity=Critical && \
  yum install -y /tmp/python-linstor-*.rpm /tmp/linstor-client*.rpm && yum clean all -y

RUN groupadd linstor
RUN useradd -m -g linstor linstor

USER linstor
ENTRYPOINT ["linstor"]
