
import os
import subprocess
import pty
import select
import fcntl
import termios
import struct
import logging
from flask import Flask, render_template, session, request, make_response, jsonify
from flask_socketio import SocketIO
from .client import ClientManager

# const
APP_SITE="https://box1.ibd.ink"

# init global variables
this_dir = os.path.dirname(os.path.realpath(__file__))
app = Flask(__name__, template_folder=os.path.join(this_dir, "templates"))
logger = app.logger
if app.debug:
    logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG if app.debug else logging.WARNING, format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s')
socketio = SocketIO(app, cors_allowed_origins=APP_SITE)
sessions = {}
client = ClientManager()
# thing below may be rubbish

# utils
def api_return(status: int, message = None) -> str:
    msg_temp = {
        200: "OK",
        400: "Wrong Arguments",
        403: "Authentication Failed or Client Not Registered",
        500: "Internal Server Error"
    }
    if not message:
        message = msg_temp[status]
    return jsonify({"status": status, "message": message}), 200

def set_winsize(fd, row, col, xpixel=0, ypixel=0):
    logging.debug("set_winsize: fd=%s, row=%s, col=%s, xpixel=%s, ypixel=%s" % (fd, row, col, xpixel, ypixel))
    
    winsize = struct.pack("HHHH", row, col, xpixel, ypixel)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)

def read_and_forward_pty_output(sid):
    max_read_bytes = 1024 * 20
    logging.debug("read_and_forward_pty_output: sid=%s" % sid)
    while True:
        socketio.sleep(0.05)
        if sid not in sessions:
            return
        if not sessions[sid]['fd']:
            continue
        logging.debug("reading from pty")
        (data_ready, _, _) = select.select([sessions[sid]["fd"]], [], [], 0)
        if not data_ready:
            continue
        try:
            output = os.read(sessions[sid]["fd"], max_read_bytes).decode(errors="ignore")
        except (OSError,KeyError,BrokenPipeError):
            break
        socketio.emit("pty-output", {"output": output}, namespace="/webshell", to=sid)
    socketio.emit("pty-output", {"output": "Connection closed\n"}, namespace="/webshell", to=sid)

# webpage
@app.route('/')
def hello_world():
    return render_template("index.html")

@app.route('/webshell')
def webshell():
    return render_template("webshell.html")

@app.route('/account')
def account():
    return render_template("account.html")


@app.route('/register')
def register():
    client_id = request.cookies.get("client_id")
    if client_id and client.check_client(client_id):
        return api_return(400, "client already registered")
    client_id = client.register(request.remote_addr)
    resp = make_response(api_return(200))
    resp.set_cookie("client_id", client_id, max_age = 34560000)
    return resp

@app.route('/list-box')
def list_box():
    client_id = request.cookies.get("client_id")
    if not client_id or not client.check_client(client_id):
        return api_return(403)
    resp = make_response(jsonify(client.get_box_fancy_list(client_id)))
    resp.set_cookie("client_id", client_id, max_age = 34560000)
    return resp

@app.route('/create-box')
def create_box():
    client_id = request.cookies.get("client_id")
    if not client_id or not client.check_client(client_id):
        return api_return(403)
    if client.create_box(client_id):
        return api_return(200)
    else:
        return api_return(400, "box creation failed. check if you exceeded the limit")

@app.route('/remove-box')
def remove_box():
    client_id = request.cookies.get("client_id")
    box_id = request.args.get("box_id")
    if not client_id or not client.check_client(client_id):
        return api_return(403)
    if not box_id:
        return api_return(400)
    if client.auth_box(client_id, box_id):
        if client.remove_box(client_id, box_id):
            return api_return(200)
        else:
            return api_return(500)
    else:
        return api_return(403, "this box does not belong to you")

@app.route('/migrate-client')
def migrate_client():
    client_id = request.cookies.get("client_id")
    to_client_id = request.args.get("to_client_id")
    if not to_client_id or not client.check_client(to_client_id):
        return api_return(403)
    if client_id and client.check_client(client_id):
        if not client.purge_client(client_id):
            return api_return(500)
    resp = make_response(api_return(200))
    resp.set_cookie("client_id", to_client_id, max_age = 34560000)
    return resp

@app.route('/remove-client')
def remove_client():
    client_id = request.cookies.get("client_id")
    if not client_id or not client.check_client(client_id):
        return api_return(403)
    if not client.purge_client(client_id):
        return api_return(500)
    resp = make_response(api_return(200))
    resp.set_cookie("client_id", "", max_age = 0)
    return resp


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
        socketio.emit("pty-output", {"output": "no box id provided\n"}, namespace="/webshell", to=sid)
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
            # logger.disable(logging.CRITICAL)
            subprocess.run(["docker", "exec", "-it", container, "zsh"])
        else:
            # this is the parent process fork.
            sessions[sid]["fd"] = fd
            sessions[sid]["child_pid"] = child_pid
            socketio.start_background_task(target=read_and_forward_pty_output, sid=sid)
    else:
        logger.error("client already connected")

        
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
