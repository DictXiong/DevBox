
import os
import subprocess
import pty
import select
import fcntl
import termios
import struct
import logging
from flask import Flask, render_template
from flask_socketio import SocketIO

# init global variables
this_dir = os.path.dirname(os.path.realpath(__file__))
app = Flask(__name__, template_folder=os.path.join(this_dir, "templates"))
logger = app.logger
logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s [line:%(lineno)d] - %(levelname)s: %(message)s')
socketio = SocketIO(app)
# thing below may be rubbish
app.config["fd"] = None
app.config["child_pid"] = None
app.config['cmd'] = ["docker", "exec", "-it", "dev", "bash"]

# utils
def set_winsize(fd, row, col, xpixel=0, ypixel=0):
    logging.debug("set_winsize: fd=%s, row=%s, col=%s, xpixel=%s, ypixel=%s" % (fd, row, col, xpixel, ypixel))
    
    winsize = struct.pack("HHHH", row, col, xpixel, ypixel)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)

def read_and_forward_pty_output():
    max_read_bytes = 1024 * 20
    while True:
        socketio.sleep(0.05)
        if app.config['fd']:
            (data_ready, _, _) = select.select([app.config["fd"]], [], [], None)
            if data_ready:
                try:
                    output = os.read(app.config["fd"], max_read_bytes).decode(
                        errors="ignore"
                    )
                except OSError:
                    socketio.emit("pty-output", {"output": "Connection closed"}, namespace="/webshell")
                    return
                socketio.emit("pty-output", {"output": output}, namespace="/webshell")


@app.route('/')
def hello_world():
    return "<h1>Welcome to Dict's DevBox</h1>\n"

@app.route('/webshell')
def webshell():
    return render_template("webshell.html")


@socketio.on("pty-input", namespace="/webshell")
def pty_input(data):
    """write to the child pty. The pty sees this as if you are typing in a real
    terminal.
    """
    if app.config["fd"]:
        logging.debug("received input from browser: %s" % data["input"])
        os.write(app.config["fd"], data["input"].encode())

@socketio.on("resize", namespace="/webshell")
def resize(data):
    if app.config["fd"]:
        logging.debug(f"Resizing window to {data['rows']}x{data['cols']}")
        set_winsize(app.config["fd"], data["rows"], data["cols"])

@socketio.on("connect", namespace="/webshell")
def connect():
    """new client connected"""
    logging.info("new client connected")
    if app.config["child_pid"]:
        # already started child process, don't start another
        return

    # create child process attached to a pty we can read from and write to
    (child_pid, fd) = pty.fork()
    if child_pid == 0:
        logging.disable(logging.CRITICAL)
        # this is the child process fork.
        # anything printed here will show up in the pty, including the output
        # of this subprocess
        subprocess.run(app.config["cmd"])
    else:
        # this is the parent process fork.
        # store child fd and pid
        app.config["fd"] = fd
        app.config["child_pid"] = child_pid
        set_winsize(fd, 50, 50)
        cmd = app.config["cmd"]
        # logging/print statements must go after this because... I have no idea why
        # but if they come before the background task never starts
        socketio.start_background_task(target=read_and_forward_pty_output)

        logging.info("child pid is " + child_pid)
        logging.info(
            f"starting background task with command `{cmd}` to continously read "
            "and forward pty output to client"
        )
        logging.info("task started")