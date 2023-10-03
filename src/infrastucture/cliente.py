from src.infrastucture.Conection import Conection
import threading
from .menu_handler import MenuHandler  # Importar la clase desde el archivo
from queue import Queue

message_queue_c_to_m = Queue()
message_queue_m_to_c = Queue()

menu_handler_instance = MenuHandler(message_queue_c_to_m,message_queue_m_to_c)
connection_instance = Conection(message_queue_c_to_m,message_queue_m_to_c)


class cliente():

    def __init__(self):
        try:
            menu_thread = threading.Thread(target=menu_handler_instance.run)
            conection_thread = threading.Thread(target=connection_instance.conexion, args=("127.0.0.1", 7000))
            menu_thread.start()
            conection_thread.start()
        except KeyboardInterrupt:
            pass
        