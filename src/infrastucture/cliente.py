from src.infrastucture.Conection import Conection
import threading
from .menu_handler import MenuHandler  # Importar la clase desde el archivo
from queue import Queue

message_queue_c_to_m = Queue()
message_queue_m_to_c = Queue()

terminate_event = threading.Event()

menu_handler_instance = MenuHandler(message_queue_c_to_m,message_queue_m_to_c,terminate_event)
connection_instance = Conection(message_queue_c_to_m,message_queue_m_to_c,terminate_event)



class cliente():

    def __init__(self):
        try:
            menu_thread = threading.Thread(target=menu_handler_instance.run)
            conection_thread = threading.Thread(target=connection_instance.conexion)
            conection_thread.start()
            menu_thread.start()
        except KeyboardInterrupt:
            pass
        