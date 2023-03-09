import os
import sqlite3
import logging

class DBManager:
    def __init__(self) -> None:
        this_dir = os.path.dirname(os.path.realpath(__file__))
        self.db_path = os.path.join(this_dir, "clients.db")
        if (not os.path.exists(self.db_path)):
            self.init_db()
        self.con = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cur = self.con.cursor()
    
    def init_db(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        cur.execute("CREATE TABLE clients(id)")
        cur.execute("CREATE TABLE boxes(id,client_id)")
        con.commit()
            
    def add_client(self, client_id):
        assert client_id
        self.cur.execute("SELECT * FROM clients WHERE id=?", (client_id,))
        if self.cur.fetchone() is not None:
            logging.error(f"Client {client_id} already exists")
            return False
        self.cur.execute("INSERT INTO clients VALUES (?)", (client_id,))
    
    # todo: not fully implemented
    def remove_client(self, client_id):
        assert client_id
        self.cur.execute("DELETE FROM clients WHERE id=?", (client_id,))
        self.cur.execute("DELETE FROM boxes WHERE client_id=?", (client_id,))
    
    def add_box(self, client_id, box_id):
        assert client_id and box_id
        self.cur.execute("SELECT * FROM boxes WHERE id=?", (box_id,))
        if self.cur.fetchone() is not None:
            return False
        self.cur.execute("INSERT INTO boxes VALUES (?,?)", (box_id, client_id))
        
    def remove_box(self, box_id):
        assert box_id
        self.cur.execute("DELETE FROM boxes WHERE id=?", (box_id,))

    def has_client(self, client_id):
        assert client_id
        self.cur.execute("SELECT * FROM clients WHERE id=?", (client_id,))
        if self.cur.fetchone() is None:
            return False
        return True

    def has_box(self, client_id, box_id):
        assert client_id and box_id
        self.cur.execute("SELECT * FROM boxes WHERE id=? AND client_id=?", (box_id, client_id))
        if self.cur.fetchone() is None:
            return False
        return True
    
    def get_box_list(self, client_id):
        if not client_id:
            return []
        self.cur.execute("SELECT * FROM boxes WHERE client_id=?", (client_id,))
        return [i[0] for i in self.cur.fetchall()]

    def get_full_box_list(self):
        self.cur.execute("SELECT * FROM boxes")
        return [i[0] for i in self.cur.fetchall()]
    
    def get_box_count(self, client_id):
        assert client_id
        self.cur.execute("SELECT * FROM boxes WHERE client_id=?", (client_id,))
        return len(self.cur.fetchall())
    
    def get_full_box_count(self):
        self.cur.execute("SELECT * FROM boxes")
        return len(self.cur.fetchall())
