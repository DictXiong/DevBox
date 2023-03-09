import time
import logging
import docker
import dateutil.parser
import datetime

CONTAINER_PREFIX = "devbox_"
CONTAINER_MAX_TTL = 60 * 60 * 24 * 7  # 7 days
IMAGE_NAME = "ubuntu:latest"

class BoxManager:
    def __init__(self) -> None:
        self.box_list = []
        self.docker_client = docker.from_env()
        for i in self.docker_client.containers.list(all=True):
            if i.name.startswith(CONTAINER_PREFIX):
                self.box_list.append(i.id)
                logging.warn(f"Box {i.id} loaded")
    
    def autoclean(self):
        for i in self.box_list:
            container = self.docker_client.containers.get(i)
            container_ttl = (datetime.datetime.now(datetime.timezone.utc) - dateutil.parser.parse(container.attrs["Created"])).total_seconds()
            if container.status != "running":
                logging.warn(f"Box {i} removed because it is not running")
                container.remove(force=True)
                self.box_list.remove(i)
            elif container_ttl > CONTAINER_MAX_TTL:
                logging.warn(f"Box {i} removed because it has run for {container_ttl} seconds")
                container.remove(force=True)
                self.box_list.remove(i)

    def check_box(self, box_id):
        return box_id in self.box_list
    
    def create_box(self, client_id):
        container = self.docker_client.containers.run(IMAGE_NAME, detach=True, name=CONTAINER_PREFIX + client_id + "_" + str(int(time.time())), command="bash", tty=True)
        logging.warn(f"Box {container.id} created")
        self.box_list.append(container.id)
        return container.id
    
    def remove_box(self, box_id):
        if box_id not in self.box_list:
            return False
        container = self.docker_client.containers.get(box_id)
        container.remove(force=True)
        self.box_list.remove(box_id)
        logging.warn(f"Box {container.id} removed")
        return True
    
    def get_box_list(self):
        return self.box_list