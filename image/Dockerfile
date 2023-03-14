FROM ubuntu:latest

RUN apt-get update -y && DEBIAN_FRONTEND=noninteractive apt-get -yq install git-all curl zsh vim \
&& (curl dotfiles.cn | bash -s - -alu root -x DFS_UPDATE_CHANNEL=dev) \
&& rm -rf /var/lib/apt/list/*

