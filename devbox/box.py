import time
import logging
import docker
import dateutil.parser
import datetime

CONTAINER_PREFIX = "devbox_"
CONTAINER_MAX_TTL = 60 * 60 * 24 * 7  # 7 days
IMAGE_NAME = "dictxiong/devbox:latest"
CONTAINER_NANO_CPUS = 1e9
CONTAINER_MEM_LIMIT = "1g"

class BoxManager:
    def __init__(self) -> None:
        self.docker_client = docker.from_env()

    def get_box_list(self):
        box_list = []
        for i in self.docker_client.containers.list(all=True):
            if i.name.startswith(CONTAINER_PREFIX):
                box_list.append(i)
                logging.warn(f"Box {i.id} loaded")
        return box_list

    def autoclean(self):
        box_list = self.get_box_list()
        for i in box_list:
            container_ttl = (datetime.datetime.now(datetime.timezone.utc) - dateutil.parser.parse(i.attrs["Created"])).total_seconds()
            if i.status != "running":
                logging.warn(f"Box {i} removed because it is not running")
                i.remove(force=True)
            elif container_ttl > CONTAINER_MAX_TTL:
                logging.warn(f"Box {i} removed because it has run for {container_ttl} seconds")
                i.remove(force=True)

    def check_box(self, box_id):
        try:
            container = self.docker_client.containers.get(box_id)
            if container.name.startswith(CONTAINER_PREFIX):
                return True
        except docker.errors.NotFound:
            logging.error(f"Box {box_id} not found")
            pass
        return False
    
    def create_box(self, client_id):
        container = self.docker_client.containers.run(IMAGE_NAME, detach=True, name=CONTAINER_PREFIX + client_id + "_" + str(int(time.time())), command="bash", tty=True, mem_limit = CONTAINER_MEM_LIMIT, nano_cpus = CONTAINER_NANO_CPUS)
        logging.warn(f"Box {container.id} created")
        return container.id
    
    def remove_box(self, box_id):
        try:
            container = self.docker_client.containers.get(box_id)
            if container.name.startswith(CONTAINER_PREFIX):
                container.remove(force=True)
                logging.warn(f"Box {container.id} removed")
                return True
        except docker.errors.NotFound:
            logging.error(f"Box {box_id} not found")
            pass
        return False
    
    def get_box_id_list(self):
        box_list = self.get_box_list()
        return [i.id for i in box_list]

    def get_box_meta(self, box_id):
        try:
            container = self.docker_client.containers.get(box_id)
            if container.name.startswith(CONTAINER_PREFIX):
                container_ttl = CONTAINER_MAX_TTL - (datetime.datetime.now(datetime.timezone.utc) - dateutil.parser.parse(container.attrs["Created"])).total_seconds()
                return {"id": container.id, "name": container.name, "create": container.attrs["Created"], "ttl": container_ttl}
        except docker.errors.NotFound:
            logging.error(f"Box {box_id} not found")
