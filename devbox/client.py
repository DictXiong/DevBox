import uuid
import time
import logging
import threading
from multiprocessing import Lock
from multiprocessing.managers import BaseManager
import sqlite3
from .box import BoxManager
from .database import DBManager

MAX_CLIENT_BOX_COUNT = 3
lock = Lock()

class ClientManager:
    def __init__(self) -> None:
        self.db_manager = DBManager()
        self.box_manager = BoxManager()
        self.autoclean_proc = threading.Thread(target=autoclean_loop, args=(self.box_manager, self.db_manager))
        self.autoclean_proc.start()

    def check_client(self, client_id):
        return self.db_manager.has_client(client_id)

    def register(self, client_ip):
        client_id = str(uuid.uuid4())
        self.db_manager.add_client(client_id, client_ip)
        return client_id

    def get_box_fancy_list(self, client_id):
        box_list = self.db_manager.get_box_list(client_id)
        return [self.box_manager.get_box_meta(i) for i in box_list]
    
    def create_box(self, client_id):
        if not self.db_manager.has_client(client_id):
            return False
        if self.db_manager.get_box_count(client_id) >= MAX_CLIENT_BOX_COUNT:
            return False
        box_id = self.box_manager.create_box(client_id=client_id)
        self.db_manager.add_box(client_id, box_id)
        return True
    
    def auth_box(self, client_id, box_id):
        if not self.db_manager.has_client(client_id):
            return False
        return self.db_manager.has_box(client_id, box_id)
    
    def remove_box(self, client_id, box_id):
        self.box_manager.remove_box(box_id)
        self.db_manager.remove_box(box_id)
        return True

# todo: run this outside
def autoclean_loop(box_manager, db_manager):
    while True:
        logging.warn("Autoclean loop started")
        box_manager.autoclean()
        time.sleep(2)
        alive_box_set = set(box_manager.get_box_id_list())
        owned_box_set = set(db_manager.get_full_box_list())
        unowned_box_set = alive_box_set - owned_box_set
        inexist_box_set = owned_box_set - alive_box_set
        logging.debug(f"alive_box_set: {alive_box_set}")
        logging.debug(f"owned_box_set: {owned_box_set}")
        logging.debug(f"unowned_box_set: {unowned_box_set}")
        logging.debug(f"inexist_box_set: {inexist_box_set}")
        for i in unowned_box_set:
            logging.warn(f"Box {i} removed because it is not owned by any client")
            box_manager.remove_box(i)
        for i in inexist_box_set:
            logging.warn(f"Box {i} removed because it does not exist")
            db_manager.remove_box(i)
        time.sleep(60)
