FROM ubuntu:latest

RUN ln -fs /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
  && apt-get update -y && DEBIAN_FRONTEND=noninteractive apt-get -yq install git-all curl zsh vim fzf \
    tmux python3 python3-pip build-essential cmake less wget bash zip htop cron supervisor \
  && (curl dotfiles.cn | bash -s - -alu root -x DFS_UPDATE_CHANNEL=dev -x ZSH_THEME=ys -x DFS_ORPHAN=1) \
  && rm -rf /var/lib/apt/list/*

ENTRYPOINT ["/usr/bin/supervisord", "-n"]

