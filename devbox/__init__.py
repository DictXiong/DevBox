
import os
import subprocess
import pty
import select
import fcntl
import termios
import struct
import logging
from flask import Flask, render_template, session, request, make_response
from flask_socketio import SocketIO
from .client import ClientManager

# init global variables
this_dir = os.path.dirname(os.path.realpath(__file__))
app = Flask(__name__, template_folder=os.path.join(this_dir, "templates"))
logger = app.logger
# logger.setLevel(logging.)
logging.basicConfig(level=logging.WARNING, format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s')
socketio = SocketIO(app)
sessions = {}
client = ClientManager()
# thing below may be rubbish

# utils
def set_winsize(fd, row, col, xpixel=0, ypixel=0):
    logging.debug("set_winsize: fd=%s, row=%s, col=%s, xpixel=%s, ypixel=%s" % (fd, row, col, xpixel, ypixel))
    
    winsize = struct.pack("HHHH", row, col, xpixel, ypixel)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)

def read_and_forward_pty_output(sid):
    max_read_bytes = 1024 * 20
    logging.debug("read_and_forward_pty_output: sid=%s" % sid)
    while True:
        socketio.sleep(0.05)
        if sessions[sid]['fd']:
            logging.debug("reading from pty")
            (data_ready, _, _) = select.select([sessions[sid]["fd"]], [], [], None)
            if data_ready:
                try:
                    output = os.read(sessions[sid]["fd"], max_read_bytes).decode(
                        errors="ignore"
                    )
                except OSError:
                    socketio.emit("pty-output", {"output": "Connection closed"}, namespace="/webshell", to=sid)
                    return
                socketio.emit("pty-output", {"output": output}, namespace="/webshell", to=sid)


@app.route('/')
def hello_world():
    return "<h1>Welcome to Dict's DevBox</h1>\n"

@app.route('/webshell')
def webshell():
    return render_template("webshell.html")

@app.route('/register')
def register():
    client_id = request.cookies.get("client_id")
    if client_id and client.check_client(client_id):
        return "Client already registered"
    client_id = client.register(request.remote_addr)
    resp = make_response("Client registered")
    resp.set_cookie("client_id", client_id, max_age = 34560000)
    return resp

@app.route('/list-box')
def list_box():
    client_id = request.cookies.get("client_id")
    if not client_id or not client.check_client(client_id):
        return "Client not registered"
    return str(client.get_box_fancy_list(client_id))

@app.route('/create-box')
def create_box():
    client_id = request.cookies.get("client_id")
    if not client_id or not client.check_client(client_id):
        return "Client not registered"
    if client.create_box(client_id):
        return "Box created"
    else:
        return "Box creation failed"


@socketio.on("pty-input", namespace="/webshell")
def pty_input(data):
    sid = request.sid
    if sid not in sessions:
        return
    logging.debug("pty_input: sid=%s" % sid)
    if sessions[sid]["fd"]:
        logging.debug("received input from browser: %s" % data["input"])
        os.write(sessions[sid]["fd"], data["input"].encode())

@socketio.on("resize", namespace="/webshell")
def resize(data):
    sid = request.sid
    if sid not in sessions:
        return
    if sessions[sid]["fd"]:
        logging.debug(f"Resizing window to {data['rows']}x{data['cols']}")
        set_winsize(sessions[sid]["fd"], data["rows"], data["cols"])

@socketio.on("connect", namespace="/webshell")
def connect():
    """new client connected"""
    sid = request.sid
    container = request.args.get("box_id")
    if not container:
        socketio.emit("pty-output", {"output": "no box id provided"}, namespace="/webshell", to=sid)
        socketio.close_room(sid)
        return
    client_id = request.cookies.get("client_id")
    if not client_id or not client.auth_box(client_id, container):
        socketio.emit("pty-output", {"output": "authentication failed or box does not exist\n"}, namespace="/webshell", to=sid)
        socketio.close_room(sid)
        return
    logging.info("new client connected: sid=%s" % sid)
    if sid not in sessions:
        logging.info("client not connected, creating new session")
        sessions[sid] = {}
        (child_pid, fd) = pty.fork()
        if child_pid == 0:
            # this is the child process fork.
            logging.disable(logging.CRITICAL)
            subprocess.run(["docker", "exec", "-it", container, "bash"])
        else:
            # this is the parent process fork.
            sessions[sid]["fd"] = fd
            sessions[sid]["child_pid"] = child_pid
            socketio.start_background_task(target=read_and_forward_pty_output, sid=sid)
    else:
        logger.error("client already connected")
        return "client already connected"
        
@socketio.on("disconnect", namespace="/webshell")
def disconnect():
    """client disconnected"""
    sid = request.sid
    logging.info("client disconnected: sid=%s" % sid)
    if sid in sessions:
        logging.info("client connected, closing session")
        os.close(sessions[sid]["fd"])
        os.kill(sessions[sid]["child_pid"], 9)
        del sessions[sid]
    else:
        logging.warn("client not connected")