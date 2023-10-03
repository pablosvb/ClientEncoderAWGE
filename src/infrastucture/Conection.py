import socket
import json

from src.application import Logger
from queue import Queue


logger = Logger.Logger()


class Conection:
    def __init__(self,queue):
        self 
        self.queue = queue
        

    def host(self):
        HOST = input("[38;5;20m Introduce el Host:[92;5;154m")
        return HOST
    
    def port(self):
        PORT = int (input("[38;5;20m Introduce el Puerto:[92;5;154m"))
        return PORT
    
    def conexion(self,HOST,PORT):
        try:
            HOST = "127.0.0.1"
            PORT = 7000
            error = False;
            logger.debug("Conectando...")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.1", 7000))
            logger.debug(f'Conectado al servidor: {HOST}:{PORT}')
            
            while True:
                # Introducimos los mensajes que se necesiten desde el terminal.
                mensaje = self.queue.get()
                s.sendall(mensaje.encode())
                data = s.recv(1024)
                print(f'[38;5;33m Server: [92;5;92m{data.decode()}')
                    
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
            try:
                s.close()
                if (error == True):
                    mensaje = input("Presione Enter para volver a introducir un HOST y un PORT.")
                    if mensaje == "salir":
                        pass
            except:
                pass
    
