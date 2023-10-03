
import queue
import time
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import sh1106
from PIL import ImageFont, ImageDraw, Image
import RPi.GPIO as GPIO
import src.domain.GPIOConstants as GC
from queue import Queue
import json

# Cargar una fuente TrueType y ajustar su tamaño
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # Ruta a una fuente ttf en tu sistema, ajusta si es necesario
font_size = 11
font_size_status = 10

font = ImageFont.truetype(font_path, font_size)
font_status = ImageFont.truetype(font_path, font_size_status)
# Configura los pines GPIO como Entradas para el Encoder.

ENCODER_PIN_A = GC.S1  # Ajustar según tu conexión
ENCODER_PIN_B = GC.S2  # Ajustar según tu conexión
BUTTON_PIN = GC.S3    # Ajustar según tu conexión

serial = i2c(port=1, address=0x3C)
device = sh1106(serial, width=128, height=64, rotate=0)
print("size: ", device.bounding_box)
device.clear()

pulsado_Atras = False
pulsado_Intro = False

Menu = 0

# diagrama de configuracion de la variable de Menu:
# 
# 
# Menu = -1 -> Oled apagada modo bajo consumo.
# Menu = 0 -> Menu principal 
# Menu = 1 -> Menu frecuencia
# Menu = 2 -> Menu Att_RCP
# Menu = 3 -> Menu Att_LCP
# Menu = 4 -> Menu ALC_Mode
# Menu = 5 -> Menu Status
# 
# 
# Menu = 10 ->Menu confirmacion
# 
#   

class MenuHandler:

    def __init__(self,queue_c_m,queue_m_c,terminate_event):
        self.terminate_event = terminate_event 
        self.queue_c_m = queue_c_m
        self.queue_m_c = queue_m_c
        self.options_menu = ["Frecuencia", "Att_RCP", "Att_LCP", "ALC_Mode", "Status"]
        self.options_frecuencia = [0,0,0,0,0,0,0,0,0,0,0]
        self.options_ALC = ["Opened", "Closed"]
        self.options_confirmacion =["SI","NO"]
        # variables menu principal
        self.menu = 0
        self.Menu0_option = 0
        # Variables menu frecuencia 
        self.Menu_Option_fr = 0
        self.fr_mult = 1
        self.CounterValue_Option_fr = 100000000
        self.magnitud = "Hz"

        # Variavles menu RCP
        self.Menu_option_RCP = 0
        self.CounterValue_RCP = 0

        # Variavles menu RCP
        self.Menu_option_LCP = 0
        self.CounterValue_LCP = 0

        # Variables menu ALC
        self.Menu_option_ALC = 0
        self.CounterValue_ALC = 0

        # Variables menu Status
        self.Menu_option_Status = 0

        self.frecuencia = 0 
        self.rf_enable = 0
        self.potencia = 0
        self.Att_RCP = 0
        self.Att_LCP = 0
        self.ALC_mode = "Opened" 
        

        # Variables menu confirmacion:
        self.Menu_option_confirmacion = 0
        self.tipo = 0

        self.counter = 0
        self.serial = serial
        self.device = device
         # Configuración de GPIO
        GPIO.setmode(GPIO.BCM)

        
        GPIO.setup(ENCODER_PIN_A, GPIO.IN,pull_up_down=GPIO.PUD_UP)
        GPIO.setup(ENCODER_PIN_B, GPIO.IN,pull_up_down=GPIO.PUD_UP)
        GPIO.setup(BUTTON_PIN, GPIO.IN,pull_up_down=GPIO.PUD_UP)

        GPIO.add_event_detect(ENCODER_PIN_A, GPIO.FALLING, callback=self.handle_encoder,bouncetime=10)
        GPIO.add_event_detect(ENCODER_PIN_B, GPIO.FALLING, callback=self.handle_encoder,bouncetime=10)
        GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, callback=self.handle_button, bouncetime=200)
        self.last_a = GPIO.input(ENCODER_PIN_A)
        self.last_b = GPIO.input(ENCODER_PIN_B)
        self.A = False
        self.B = False

         # Mostrar el menú cuando iniciamos el controlador
        self.image_path = '/home/awge/ClientEncoderAWGE/src/infrastucture/logo.png'
       
        self.display_Logo()
        # tiempo para el encendido y todas las conexiones 
        time.sleep(4)
        conec = True
        """
        while conec:
            try:
                mensaje = self.queue_c_m.get(timeout=2)
            except queue.Empty:
                mensaje = "nada"
            
            print("mensaje: "+ mensaje)
            if mensaje == "Conectado":
                conec = False
            else:
                self.display_Erro()
        """
        self.display_option()


    def display_Solv(self):
        with canvas(self.device) as draw: 
            draw.text((10, 20), "Inicializando", font=font, fill="white")
            draw.text((0,40),"Servidor conectado", font=font, fill="white")    

    def display_Erro(self):
        with canvas(self.device) as draw: 
            draw.text((10, 20), "Inicializando", font=font, fill="white")
            draw.text((0,35),"Conectando servidor", font=font, fill="white")
    
    def display_Logo(self):
        with Image.open(self.image_path) as img:
        # Es posible que desees redimensionar o adaptar la imagen al tamaño específico de tu OLED
            img = img.resize(device.size, Image.LANCZOS)
            img = img.convert("1")
            device.display(img)

    def display_option(self):
        with canvas(self.device) as draw: 
            for i, option in enumerate(self.options_menu):
                y_position = i * 12
                if i == self.Menu0_option:
                    draw.text((0, y_position), "▶ " + option, font=font, fill="white")
                    print(f"-> {option}")
                else:
                    draw.text((0, y_position), "   " + option, font=font, fill="white")
                    print(f"   {option}")
    
    def display_option_frecuencia(self):
        with canvas(self.device) as draw: 
            draw.text((10, 0), "Frecuencia:  "+self.magnitud, font=font, fill="white")
            draw.rectangle([(7, 28), (118, 55)], outline="white")
            draw.text((10,30),"{:011}".format(self.CounterValue_Option_fr)+"Hz",font=font, fill="white")
            for i, option in enumerate(self.options_frecuencia):
                x_position = 90 - i * 8
                if i == self.Menu_Option_fr:
                    draw.text((x_position, 40), "▲" , font=font, fill="white")
                else:
                    draw.text((x_position, 40), " " , font=font, fill="white")

    def display_option_RCP(self):
        with canvas(self.device) as draw: 
            draw.text((10, 0), "Atenuador RCP:", font=font, fill="white")
            draw.text((50,30),str(self.CounterValue_RCP)+" dB",font=font, fill="white")
    
    def display_option_LCP(self):
        with canvas(self.device) as draw: 
            draw.text((10, 0), "Atenuador LCP:", font=font, fill="white")
            draw.text((50,30),str(self.CounterValue_LCP)+" dB",font=font, fill="white")
    
    
    def display_option_ALC(self):
        with canvas(self.device) as draw: 
            draw.text((30, 0), "Modo ALC:  ", font=font, fill="white")
            draw.text((10,40),"Opened   Closed",font=font, fill="white")
            for i, option in enumerate(self.options_ALC):
                x_position = 85 - i * 55
                if i == self.Menu_option_ALC:
                    draw.text((x_position, 50), "▲" , font=font, fill="white")
                else:
                    draw.text((x_position, 50), " " , font=font, fill="white")
    
    def display_option_Status(self):
        if self.Menu_option_Status == 0:
            with canvas(self.device) as draw: 
                draw.rectangle([(0, 0), (127, 25)], outline="white")
                draw.text((30,0), "Frecuencia:  ", font=font_status, fill="white")
                draw.text((17,10),"{:011}".format(self.frecuencia)+"Hz",font=font_status, fill="white")
                draw.text((0,26), "RF_Enable: "+str(bool(self.rf_enable)), font=font_status, fill="white")
                draw.line([(0, 38), (128, 38)], fill="white")
                draw.text((0,38),"Power: "+str(self.potencia)+"dB",font=font_status, fill="white")
                draw.line([(0, 50), (128, 50)], fill="white")
                draw.text((0,50), "ALC_Mode:"+self.ALC_mode, font=font_status, fill="white")
        elif self.Menu_option_Status == 1:
            with canvas(self.device) as draw: 
                draw.text((0, 0), "Att_RCP:  "+str(self.Att_RCP)+"dB", font=font_status, fill="white")
                draw.line([(0, 15), (128, 15)], fill="white")
                draw.text((0, 15), "Att_LCP:  "+str(self.Att_LCP)+"dB", font=font_status, fill="white")
    
    
    def display_Confirmacion(self,tipo,variable):
        with canvas(self.device) as draw: 
            draw.text((2, 0), "Quieres confirmar?  ", font=font, fill="white")
            if tipo == 1: #nos indica que el cambio es de frecuencia
                draw.text((22,12),"Frecuencia:",font=font, fill="white")
                draw.text((10,25),"{:011}".format(variable)+"Hz",font=font, fill="white")
                draw.text((30,40),"SI          NO",font=font, fill="white")
                for i, option in enumerate(self.options_confirmacion):
                    x_position = 85 - i * 55
                    if i == self.Menu_option_confirmacion:
                        draw.text((x_position, 50), "▲" , font=font, fill="white")
                    else:
                        draw.text((x_position, 50), " " , font=font, fill="white")
            if tipo == 2: #no indica que el cambio es de RCP
                draw.text((8,12),"Atenuacion RCP:",font=font, fill="white")
                draw.text((50,25),str(variable)+"dB",font=font, fill="white")
                draw.text((30,40),"SI          NO",font=font, fill="white")
                for i, option in enumerate(self.options_confirmacion):
                    x_position = 85 - i * 55
                    if i == self.Menu_option_confirmacion:
                        draw.text((x_position, 50), "▲" , font=font, fill="white")
                    else:
                        draw.text((x_position, 50), " " , font=font, fill="white")
            if tipo == 3: #no indica que el cambio es de LCP
                draw.text((8,12),"Atenuacion LCP:",font=font, fill="white")
                draw.text((50,25),str(variable)+"dB",font=font, fill="white")
                draw.text((30,40),"SI          NO",font=font, fill="white")
                for i, option in enumerate(self.options_confirmacion):
                    x_position = 85 - i * 55
                    if i == self.Menu_option_confirmacion:
                        draw.text((x_position, 50), "▲" , font=font, fill="white")
                    else:
                        draw.text((x_position, 50), " " , font=font, fill="white")
  
    def next_option(self):
        self.Menu0_option += 1
        if self.Menu0_option == len(self.options_menu):
            self.Menu0_option = 0
        print(self.Menu0_option)
        self.display_option()

    def previous_option(self):
        self.Menu0_option -= 1
        if self.Menu0_option < 0:
            self.Menu0_option = len(self.options_menu) - 1
        print(self.Menu0_option)
        self.display_option()

    def next_option_Fr(self):
        self.CounterValue_Option_fr += 1*self.fr_mult
        if self.CounterValue_Option_fr > 20000000000 :
            self.CounterValue_Option_fr = 100000000
        print("Menu_opcion_fr: "+ str(self.Menu_Option_fr) + " value fr: "+"{:011}".format(self.CounterValue_Option_fr)+"Hz")
        self.select_option_Fr()

    def previous_option_Fr(self):
        self.CounterValue_Option_fr -= 1 * self.fr_mult
        if self.CounterValue_Option_fr < 100000000:
            self.CounterValue_Option_fr = 20000000000
        print("Menu_opcion_fr: "+str(self.Menu_Option_fr) + " value fr: "+"{:011}".format(self.CounterValue_Option_fr)+"Hz")
        self.select_option_Fr()

    def next_option_RCP(self):
        self.CounterValue_RCP += 1
        if self.CounterValue_RCP > 31 :
            self.CounterValue_RCP = 0
        print("RCP: "+str(self.CounterValue_RCP)+" dB")
        self.select_option_RCP()

    def previous_option_RCP(self):
        self.CounterValue_RCP -= 1
        if self.CounterValue_RCP < 0:
            self.CounterValue_RCP = 31
        print("RCP: "+str(self.CounterValue_RCP)+" dB")
        self.select_option_RCP()

    def next_option_LCP(self):
        self.CounterValue_LCP += 1
        if self.CounterValue_LCP > 31 :
            self.CounterValue_LCP = 0
        print("RCP: "+str(self.CounterValue_LCP)+" dB")
        self.select_option_LCP()

    def previous_option_LCP(self):
        self.CounterValue_LCP -= 1
        if self.CounterValue_LCP < 0:
            self.CounterValue_LCP = 31
        print("RCP: "+str(self.CounterValue_LCP)+" dB")
        self.select_option_LCP()

    def next_option_ALC(self): # al ser una solucion vinaria solo hace falta un modificador para el encoder.
        self.Menu_option_ALC += 1
        if self.Menu_option_ALC > 1 :
            self.Menu_option_ALC = 0
        print("Menu_option_confirmacion: "+ str(self.Menu_option_ALC))
        self.select_option_ALC()

    def next_option_Status(self): # al ser una solucion vinaria solo hace falta un modificador para el encoder.
        self.Menu_option_Status += 1
        if self.Menu_option_Status > 1 :
            self.Menu_option_Status = 0
        print("Menu_option_Status: "+ str(self.Menu_option_Status))
        self.select_option_Status()

    def next_option_Confirmacion(self): # al ser una solucion vinaria solo hace falta un modificador para el encoder.
        self.Menu_option_confirmacion += 1
        if self.Menu_option_confirmacion > 1 :
            self.Menu_option_confirmacion = 0
        print("Menu_option_confirmacion: "+ str(self.Menu_option_confirmacion))
        self.menu_confirmacion()

    
    def select_option(self):
        # Aquí defines lo que ocurre cuando se selecciona una opción
        selected = self.options_menu[self.Menu0_option]
        # En lugar de imprimir en consola, muestra en la OLED:
        if selected == "Frecuencia":
            self.menu=1
            self.select_option_Fr()
        elif selected == "Att_RCP":
            self.menu=2
            self.select_option_RCP()
        elif selected == "Att_LCP":
            self.menu=3
            self.select_option_LCP()
        elif selected == "ALC_Mode":
            self.menu=4
            self.select_option_ALC()
        elif selected == "Status":
            print("dentro")
            self.queue_m_c.put("get_status_cm")
            valor=self.queue_c_m.get()
            data = json.loads(valor)

            self.frecuencia = data["rf"] 
            self.rf_enable = data["enable"] 
            self.potencia = data["power"] 
            self.Att_RCP = data["RCP"] 
            self.Att_LCP = data["LCP"] 
            self.ALC_mode = data["ALC"]  

            print("valor = "+valor)
            self.menu=5
            self.select_option_Status()

    def select_option_Fr(self):
        # Aquí defines lo que ocurre cuando se selecciona una opción
        #selected = self.options0[self.Menu0_option]
        # En lugar de imprimir en consola, muestra en la OLED:
        self.display_option_frecuencia()
    
    def select_option_RCP(self):
        # Aquí defines lo que ocurre cuando se selecciona una opción
        #selected = self.options0[self.Menu0_option]
        # En lugar de imprimir en consola, muestra en la OLED:
        self.display_option_RCP()

    def select_option_LCP(self):
        # Aquí defines lo que ocurre cuando se selecciona una opción
        #selected = self.options0[self.Menu0_option]
        # En lugar de imprimir en consola, muestra en la OLED:
        self.display_option_LCP()

    def select_option_ALC(self):
        # Aquí defines lo que ocurre cuando se selecciona una opción
        #selected = self.options0[self.Menu0_option]
        # En lugar de imprimir en consola, muestra en la OLED:
        self.display_option_ALC()

    def select_option_Status(self):
        # Aquí defines lo que ocurre cuando se selecciona una opción
        #selected = self.options0[self.Menu0_option]
        # En lugar de imprimir en consola, muestra en la OLED:
        self.display_option_Status()

        
    def handle_encoder(self, channel):
        print(channel)

        current_a = GPIO.input(ENCODER_PIN_A)
        current_b = GPIO.input(ENCODER_PIN_B)

        
        
        if channel == ENCODER_PIN_A:
            print(f"+  : {current_a}   {current_b}")
            if current_b != current_a:
                if self.menu == 0:
                    self.next_option()
                elif self.menu == 1:
                    self.next_option_Fr()
                elif self.menu == 2:
                    self.next_option_RCP()
                elif self.menu == 3:
                    self.next_option_LCP()
                elif self.menu == 4:
                    self.next_option_ALC()
                elif self.menu == 5:
                    self.next_option_Status()
                elif self.menu == 10:
                    self.next_option_Confirmacion()
                else:
                    print("Standby")

        else:
            print(f"-  : {current_a}   {current_b}")
            if current_a != current_b:
                if self.menu == 0:
                    self.previous_option()
                elif self.menu == 1:
                    self.previous_option_Fr()
                elif self.menu == 2:
                    self.previous_option_RCP()
                elif self.menu == 3:
                    self.previous_option_LCP()
                elif self.menu == 4:
                    self.next_option_ALC()
                elif self.menu == 5:
                    self.next_option_Status()
                elif self.menu == 10:
                    self.next_option_Confirmacion()
                else:
                    print("Standby")
    
    
    def menu_confirmacion(self):
        #en esta funcion confirmaremos el tipo de operacion
        # 1 - frecuencia
        # 2 - Att_RCP
        # 3 - Att_LCP
        # 4 - Menu ALC_Mode
        # 5 - Menu Status
        # dependiendo de ello mostraremos un solucion u otra:
        if self.tipo == 1:
            self.display_Confirmacion(self.tipo,self.CounterValue_Option_fr)
        elif self.tipo == 2:
            self.display_Confirmacion(self.tipo,self.CounterValue_RCP)
        elif self.tipo == 3:
            self.display_Confirmacion(self.tipo,self.CounterValue_LCP)

    def handle_button(self, channel):
        start_time = time.time()
        #print(len(self.options0))
        while GPIO.input(BUTTON_PIN) == 0:  # Esperar mientras esté presionado
            time.sleep(0.01)
            
        end_time = time.time()
        if (end_time - start_time) > 1.5:  # Si se presionó más de 5 segundos
            #denpendiendo del lugar en el que estemos haremos una cosa u otra
            # si estamos en el menu principal apagaremos la pantalla.
            if self.menu == 0:
                self.menu = -1
                self.device.hide()
            elif self.menu == 1:
                # ahora entramos en las opciones que hace el boton en este menu de Frecuencia:
                # lo que haremos en este caso es confirmar si guardamos el nuevo valor de Frecuencia:
                self.tipo=1
                # para esto cargamos un menu de confirmacion: ese menu va a ser el valor 10 de la variable menu:
                self.menu = 10
                self.menu_confirmacion()
           
        elif(end_time - start_time) > 0.1 and (end_time - start_time) < 1 :
            if self.menu == -1:
                self.device.show()
                self.display_Logo()
                time.sleep(2)
                self.menu = 0
            elif self.menu == 0:
                self.select_option()
            elif self.menu == 1:
                # ahora entramos en las opciones que hace el boton en este menu de Frecuencia:
                # cada vez que pulsemo en este menu aumentamos el multiplicador.
                self.Menu_Option_fr += 1
                if self.Menu_Option_fr == len(self.options_frecuencia):
                    self.Menu_Option_fr = 0
                # y lo que hacemos es que cada vez que pulsemos generaremos un multiplicador por 10 hasta llegar a Gz que es 10*10 a 9
                # Este es el de hz x 1 
                if self.Menu_Option_fr == 0:
                    self.magnitud = "Hz"
                    self.fr_mult = 1
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 1:
                    self.fr_mult = 10
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 2:
                    self.fr_mult = 100
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 3:
                    self.magnitud = "KHz"
                    self.fr_mult = 1000
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 4:
                    self.fr_mult = 10000
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 5:
                    self.fr_mult = 100000
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 6:
                    self.magnitud = "MHz"
                    self.fr_mult = 1000000
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 7:
                    self.fr_mult = 10000000
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 8:
                    self.fr_mult = 100000000
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 9:
                    self.magnitud = "GHz"
                    self.fr_mult = 1000000000
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 10:
                    self.fr_mult = 1000000000
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 11:
                    self.fr_mult = 1000000000
                    self.select_option_Fr()
                # aceptaremos lo que tengamos en el menu.
            elif self.menu == 2:
                # codigo para RCP
                self.tipo=2
                # para esto cargamos un menu de confirmacion: ese menu va a ser el valor 10 de la variable menu:
                self.menu = 10
                self.menu_confirmacion()
            elif self.menu == 3:
                # codigo para LCP
                self.tipo=3
                # para esto cargamos un menu de confirmacion: ese menu va a ser el valor 10 de la variable menu:
                self.menu = 10
                self.menu_confirmacion()
            elif self.menu == 4:
                # codigo para ALC
                if self.Menu_option_ALC == 0 :
                    # la opcion seleccionada es CLOSED.
                    print("ALC modificado a closed")
                    self.queue_m_c.put("set_alc_mode=closed")
                    ## enviamos la canfiguracion al servidor
                    self.menu=0
                    self.display_option()
                else:
                    # la opcion seleccionada es Opened.
                    print("ALC modificado a opened")
                    self.queue_m_c.put("set_alc_mode=opened")

                    ## enviamos la canfiguracion al servidor
                    self.menu=0
                    self.display_option()

            elif self.menu == 5:
                # codigo para Status, es solo de visualizacion asique salimos si pulsamos.
                self.menu=0
                self.display_option()


            elif self.menu == 10:
                if self.tipo == 1: #Confirmamos la configuracion de Frecuencia.
                    if self.Menu_option_confirmacion == 0 :
                        # la confirmacion es negativa por lo que salimos sin hacer nada.
                        print("modificacion de Frecuencia cancelada")
                        self.menu=0
                        self.display_option()
                    else:
                        # la confirmacion es positiva por lo que tendremos que enviar el valor al servidor con la funcion set_fr = valor confirmado.
                        print("Frecuencia modificada:"+str(self.CounterValue_Option_fr)+"Hz")
                        self.queue_m_c.put("set_rf="+str(self.CounterValue_Option_fr))
                        self.menu=0
                        self.display_option()

                if self.tipo == 2: # Confirmamos la configuracion de RCP
                    if self.Menu_option_confirmacion == 0 :
                        # la confirmacion es negativa por lo que salimos sin hacer nada.
                        print("modificacion de RCP cancelada")
                        self.menu=0
                        self.display_option()
                    else:
                        # la confirmacion es positiva por lo que tendremos que enviar el valor al servidor con la funcion set_fr = valor confirmado.
                        print("RCP modificada:"+str(self.CounterValue_RCP)+"dB")
                        self.queue_m_c.put("set_att_rcp="+str(self.CounterValue_RCP))
                        self.menu=0
                        self.display_option()

                if self.tipo == 3: # Confirmamos la configuracion de LCP
                    if self.Menu_option_confirmacion == 0 :
                        # la confirmacion es negativa por lo que salimos sin hacer nada.
                        print("modificacion de LCP cancelada")
                        self.menu=0
                        self.display_option()
                    else:
                        # la confirmacion es positiva por lo que tendremos que enviar el valor al servidor con la funcion set_fr = valor confirmado.
                        print("LCP modificada:"+str(self.CounterValue_LCP)+"dB")
                        self.queue_m_c.put("set_att_lcp="+str(self.CounterValue_LCP))
                        self.menu=0
                        self.display_option()

    def run(self):
        try:
            while not self.terminate_event.is_set():
            # ... tu código ...
            
            # Simulando alguna operación, puedes eliminar el sleep si no lo necesitas
               pass
        except KeyboardInterrupt:
            GPIO.cleanup()
            self.terminate_event.set()