from src.infrastucture.Conection import Conection
import threading
from .menu_handler import MenuHandler  # Importar la clase desde el archivo

class cliente():

    def __init__(self):
        def start_menu():
            menu = MenuHandler()
            menu.run()
        try:
            menu_thread = threading.Thread(target=start_menu)
            menu_thread.start()
        except KeyboardInterrupt:
            pass
        finally:
            while True:
                Conection.conexion("127.0.0.1",7000)


