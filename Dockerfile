FROM ubuntu:xenial as builder
MAINTAINER Roland Kammerer <roland.kammerer@linbit.com>

ENV LINSTOR_CLI_VERSION 0.1
ENV LINSTOR_CLI_PKGNAME linstor-client
ENV LINSTOR_TAR_BALL ${LINSTOR_CLI_PKGNAME}-${LINSTOR_CLI_VERSION}.tar.gz

RUN groupadd makepkg
RUN useradd -m -g makepkg makepkg

RUN apt-get update -y

RUN apt-get install -y bash-completion debhelper devscripts docbook-xsl help2man protobuf-compiler python-all python-protobuf xsltproc
COPY /dist/${LINSTOR_TAR_BALL} /tmp/

USER makepkg
RUN cd ${HOME} && \
		 cp /tmp/${LINSTOR_TAR_BALL} ${HOME} && \
		 tar xvf ${LINSTOR_TAR_BALL} && \
		 cd ${LINSTOR_CLI_PKGNAME}-${LINSTOR_CLI_VERSION} && \
		 make deb

FROM ubuntu:xenial
COPY --from=builder /home/makepkg/*.deb /tmp
RUN apt-get update -y && apt-get install -y python-natsort python-protobuf && dpkg -i /tmp/*.deb && rm /tmp/*.deb && apt-get clean -y

ENTRYPOINT ["linstor"]
