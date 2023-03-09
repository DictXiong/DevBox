import uuid
import time
import logging
import multiprocessing
import sqlite3
from .box import BoxManager
from .database import DBManager

MAX_CLIENT_BOX_COUNT = 3

class ClientManager:
    def __init__(self) -> None:
        self.db_manager = DBManager()
        self.box_manager = BoxManager()
        self.autoclean_proc = multiprocessing.Process(target=self.autoclean_loop)
        self.autoclean_proc.start()
    
    def check_client(self, client_id):
        return self.db_manager.has_client(client_id)

    def register(self):
        client_id = str(uuid.uuid4())
        self.db_manager.add_client(client_id)
        return client_id

    def get_box_list(self, client_id):
        return self.db_manager.get_box_list(client_id)
    
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
    
    def cleanup(self):
        alive_box_set = set(self.box_manager.get_box_list())
        owned_box_set = set(self.db_manager.get_full_box_list())
        unowned_box_set = alive_box_set - owned_box_set
        inexist_box_set = owned_box_set - alive_box_set
        for i in unowned_box_set:
            logging.warn(f"Box {i} removed because it is not owned by any client")
            self.box_manager.remove_box(i)
        for i in inexist_box_set:
            logging.warn(f"Box {i} removed because it does not exist")
            self.db_manager.remove_box(i)
    
    def autoclean_loop(self):
        while True:
            logging.warn("Autoclean loop started")
            self.box_manager.autoclean()
            time.sleep(2)
            self.cleanup()
            time.sleep(58)