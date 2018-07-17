FROM ubuntu:xenial as builder

ENV PYTHON_LINSTOR_VERSION 0.2.2
ENV PYTHON_LINSTOR_PKGNAME python-linstor
ENV PYTHON_LINSTOR_TGZ ${PYTHON_LINSTOR_PKGNAME}-${PYTHON_LINSTOR_VERSION}.tar.gz

ENV LINSTOR_CLI_VERSION 0.2.2
ENV LINSTOR_CLI_PKGNAME linstor-client
ENV LINSTOR_TGZ ${LINSTOR_CLI_PKGNAME}-${LINSTOR_CLI_VERSION}.tar.gz

RUN groupadd makepkg # !lbbuild
RUN useradd -m -g makepkg makepkg # !lbbuild

RUN apt-get update -y # !lbbuild

RUN apt-get install -y bash-completion debhelper devscripts docbook-xsl help2man protobuf-compiler python-setuptools python-all python-protobuf xsltproc # !lbbuild

COPY /dist/${PYTHON_LINSTOR_TGZ} /tmp/
COPY /dist/${LINSTOR_TGZ} /tmp/

USER makepkg
RUN cd ${HOME} && \
		 cp /tmp/${PYTHON_LINSTOR_TGZ} ${HOME} && \
		 tar xvf ${PYTHON_LINSTOR_TGZ} && \
		 cd ${PYTHON_LINSTOR_PKGNAME}-${PYTHON_LINSTOR_VERSION} && \
		 make gensrc && \
		 make deb
RUN cd ${HOME} && \
		 cp /tmp/${LINSTOR_TGZ} ${HOME} && \
		 tar xvf ${LINSTOR_TGZ} && \
		 cd ${LINSTOR_CLI_PKGNAME}-${LINSTOR_CLI_VERSION} && \
		 make deb

FROM ubuntu:xenial
MAINTAINER Roland Kammerer <roland.kammerer@linbit.com>
COPY --from=builder /home/makepkg/*.deb /tmp/
RUN apt-get update -y && apt-get install -y python-natsort python-protobuf && dpkg -i /tmp/*.deb && rm /tmp/*.deb && apt-get clean -y

ENTRYPOINT ["linstor"]
