import queue
import select
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
            s.settimeout(5)  # Establece un timeout de 5 segundos
            try:
                logger.debug("Conectando...")
                s.connect((HOST, PORT))
                logger.debug(f'Conectado al servidor: {HOST}:{PORT}')
                self.queue_c_m.put("conectado")
                while not self.terminate_event.is_set():
            # Verifica si hay mensajes para enviar al servidor sin bloquear
                    try:
                        mensaje = self.queue_m_c.get(timeout=0.1)  # Intenta obtener un mensaje con un timeout de 0.1 segundos
                        print("imprimiendo mensaje:"+ mensaje)
                        s.sendall(mensaje.encode())
                    except queue.Empty:  # No hay mensajes para enviar
                        pass

                    # Escucha mensajes del servidor sin bloquear
                    ready_to_read, _, _ = select.select([s], [], [], 0.1)  # Verifica si hay datos en el socket para leer con un timeout de 0.1 segundos
                    if ready_to_read:  # Si hay datos para leer
                        data = s.recv(1024)
                        if not data:
                            print("Conexión cerrada por el servidor.")
                            break
                        if mensaje == "get_status_cm":
                            self.queue_c_m.put(data.decode())
                        print(f'Server:{data.decode()}')   

                        datos = data.decode()
                        datos_lower = datos.lower()
                        Comand = datos_lower.replace("=","")
                        list_Comand = Comand.split()
                        
                        print(f'Dato:{list_Comand[0]}') 
                        if len(list_Comand)<2:
                            list_Comand.append("p")
                        
                        elif list_Comand[0] == "set_rcp":
                            num = int(list_Comand[1])
                            jsonString = '{"X":"rcp","rcp":'+str(num)+'}'
                            self.queue_c_m.put(jsonString)

                        elif list_Comand[0] == "set__lcp":
                            num = int(list_Comand[1])
                            jsonString = '{"X":"rcp","rcp":'+str(num)+'}'
                            self.queue_c_m.put(jsonString)
                        elif list_Comand[0] == "get_rcp":
                            self.queue_c_m.put("get_rcp")
                        elif list_Comand[0] == "get_lcp":
                            self.queue_c_m.put("get_lcp") 
                            
                    

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
                self.queue_c_m.put("error")
                if mensaje == "salir":
                    self.terminate_event.set()
                time.sleep(2)
                
    
