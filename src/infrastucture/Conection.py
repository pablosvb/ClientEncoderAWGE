import socket
import time 
from src.application import Logger
from queue import Queue


logger = Logger.Logger()


class Conection:
    def __init__(self,queue_c_m,queue_m_c,terminate_event):
        self.terminate_event = terminate_event
        self.queue_m_c = queue_m_c
        self.queue_c_m = queue_c_m
        

    def host(self):
        HOST = input("[38;5;20m Introduce el Host:[92;5;154m")
        return HOST
    
    def port(self):
        PORT = int (input("[38;5;20m Introduce el Puerto:[92;5;154m"))
        return PORT
    
    def conexion(self):
        
        HOST = "127.0.0.1"
        PORT = 7000
        error = False
        mensaje = ""
        while not self.terminate_event.is_set():  # Principal loop de ejecución
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                logger.debug("Conectando...")
                s.connect((HOST, PORT))
                logger.debug(f'Conectado al servidor: {HOST}:{PORT}')
                self.queue_c_m.put("Conectado")

                while not self.terminate_event.is_set():
                    mensaje = self.queue_m_c.get()
                    print("imprimiendo mensaje:"+ mensaje)
                    s.sendall(mensaje.encode())
                    data = s.recv(1024)
                    if mensaje == "get_status_cm":
                        self.queue_c_m.put(data.decode())
                    print(f'Server:{data.decode()}')

            except socket.gaierror as e:
                error = True
                if e.errno == 11001:
                    logger.debug('ERROR 11001: Los Datos de HOST Y PUERTO introducidos no son correctos')
                else:
                    logger.debug(f'Error gaierror: {e}')

            except socket.timeout as e:
                error = True
                if e.errno == 10060:
                    logger.debug('ERROR 10060: Se ha agotado el tiempo de espera para la conexión. El servidor no ha respondido a tiempo., puede que introduzca mal el HOST u/o el PORT')
                elif e.errno == 10061:
                    logger.debug("ERROR 10061: No se puede establecer una conexión ya que el equipo de destino denegó expresamente dicha conexión, puede que introduzca mal el HOST u/o el PORT")

            except Exception as e:
                error = True
                logger.debug(f'ERROR: {e}')

            finally:
                s.close()

            if error and not self.terminate_event.is_set():
                logger.debug("Esperando para Reconexion ... ")
                self.queue_c_m.put("Esperando para Reconexion")
                if mensaje == "salir":
                    self.terminate_event.set()
                time.sleep(2)
    
