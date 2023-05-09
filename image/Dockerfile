FROM ubuntu:latest

RUN ln -fs /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
  && sed -i "s@http://.*archive.ubuntu.com@http://192.168.16.201/mirrors@g" /etc/apt/sources.list \
  && apt-get update -y && DEBIAN_FRONTEND=noninteractive apt-get -yq install git-all curl zsh vim fzf \
    tmux python3 python3-pip build-essential cmake less wget bash zip htop cron supervisor \
  && (curl dotfiles.cn | bash -s - -alu root -x DFS_UPDATE_CHANNEL=dev -x DFS_THEME=ys -x DFS_ORPHAN=1) \
  && rm -rf /var/lib/apt/list/*

