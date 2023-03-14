FROM ubuntu:latest

RUN apt-get update -y && DEBIAN_FRONTEND=noninteractive apt-get -yq install git-all curl zsh vim fzf \
&& (curl dotfiles.cn | bash -s - -alu root -x DFS_UPDATE_CHANNEL=dev -x DFS_THEME=ys -x DFS_ORPHAN=1) \
&& rm -rf /var/lib/apt/list/* /.dockerenv

