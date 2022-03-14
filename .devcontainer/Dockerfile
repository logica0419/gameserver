# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.192.0/containers/python-3/.devcontainer/base.Dockerfile
ARG VARIANT="3.10"

FROM mcr.microsoft.com/vscode/devcontainers/python:0-${VARIANT}

# [Optional] Uncomment this section to install additional OS packages.
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
  && apt-get -y install --no-install-recommends bash-completion \
  default-libmysqlclient-dev default-mysql-client default-mysql-server \
  vim && \
  curl -L https://git.io/dpkg-i-from-url | bash -s -- https://github.com/k1LoW/tbls/releases/download/v1.54.2/tbls_1.54.2-1_amd64.deb

# [Optional] If your pip requirements rarely change, uncomment this section to add them to the image.
#COPY requirements.txt /tmp/pip-tmp/
#RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
#   && rm -rf /tmp/pip-tmp
