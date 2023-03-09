import uuid
import time
import logging
import threading
from .box_manager import BoxManager

MAX_CLIENT_BOX_COUNT = 3

class Client:
    def __init__(self) -> None:
        self.boxes = []

    def add_box(self, box_id):
        if box_id not in self.boxes:
            self.boxes.append(box_id)
            
    def del_box(self, box_id):
        if box_id in self.boxes:
            self.boxes.remove(box_id)
            
    def has_box(self, box_id):
        return box_id in self.boxes
    
    def get_box_list(self):
        return self.boxes
    
    def get_box_count(self):
        return len(self.boxes)


class ClientManager:
    def __init__(self) -> None:
        self.clients = {}
        self.box_manager = BoxManager()
        threading.Thread(target=self.autoclean_loop).start()
    
    def check_client(self, client_id):
        return client_id in self.clients
    
    def register(self):
        client_id = str(uuid.uuid4())
        self.clients[client_id] = Client()
        return client_id

    def get_box_list(self, client_id):
        if client_id not in self.clients:
            return []
        return self.clients[client_id].get_box_list()
    
    def create_box(self, client_id):
        if client_id not in self.clients:
            return False
        if self.clients[client_id].get_box_count() >= MAX_CLIENT_BOX_COUNT:
            return False
        box_id = self.box_manager.create_box(client_id=client_id)
        self.clients[client_id].add_box(box_id)
        return True
    
    def auth_box(self, client_id, box_id):
        if client_id not in self.clients:
            return False
        return self.clients[client_id].has_box(box_id)
    
    def cleanup(self):
        alive_box_list = self.box_manager.get_box_list()
        owned_box_list = []
        for client_id,i in self.clients.items():
            for box_id in i.get_box_list():
                if not box_id in alive_box_list:
                    i.del_box(box_id)
                    logging.warn(f"Box {box_id} removed from client {client_id}")
                else:
                    owned_box_list.append(box_id)
        for box_id in alive_box_list:
            if not box_id in owned_box_list:
                logging.warn(f"Box {box_id} removed because it is not owned by any client")
                self.box_manager.remove_box(box_id)
    
    def autoclean_loop(self):
        while True:
            logging.warn("Autoclean loop started")
            self.box_manager.autoclean()
            time.sleep(2)
            self.cleanup()
            time.sleep(58)