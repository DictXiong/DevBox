export DEVBOX_ROOT=$( cd "$( dirname "${BASH_SOURCE[0]:-${(%):-%x}}" )" && cd .. && pwd )

PYTHONPATH=$DEVBOX_ROOT:$PYTHONPATH python3 -m devbox.main $@