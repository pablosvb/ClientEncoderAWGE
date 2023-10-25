
import os
import queue
import time
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import sh1106
from PIL import ImageFont, ImageDraw, Image , ImageOps
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

emergencia_size = (45, 45)

# Configura los pines GPIO como Entradas para el Encoder.

ENCODER_PIN_A = GC.S1  # Ajustar según tu conexión
ENCODER_PIN_B = GC.S2  # Ajustar según tu conexión
BUTTON_PIN = GC.S3    # Ajustar según tu conexión

# Lista de pines GPIO a controlar (0-31)
gpioA1_pins = [GC.A1C16, GC.A1C8, GC.A1C4, GC.A1C2, GC.A1C1]  # Por ejemplo, aquí están los pines GPIO que se utilizarán
gpioA2_pins = [GC.A2C16, GC.A2C8, GC.A2C4, GC.A2C2, GC.A2C1]  # Por ejemplo, aquí están los pines GPIO que se utilizarán
# Pin adicional para LA (Latch)
laA1_pin = GC.A1LE
laA2_pin = GC.A2LE


serial = i2c(port=1, address=0x3C)
device = sh1106(serial, width=128, height=64, rotate=0)
device.clear()

pulsado_Atras = False
pulsado_Intro = False

DEBOUNCE_TIME = 0.01  # tiempo en segundos, ajusta según sea necesario

last_interrupt_time = 0
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
        self.options_menu = ["Frecuencia", "Att_RCP", "Att_LCP", "Ref_Clock", "Status"]
        self.options_frecuencia = [0,0,0,0,0,0,0,0,0,0,0]
        self.options_Ref_Clock = ["External", "Internal"]
        self.options_confirmacion =["SI","NO"]
        # variables menu principal
        self.menu = 0
        self.Menu0_option = 0
        self.selected = ""

        self.errorsistema = False


        # Variables menu frecuencia 
        self.Menu_Option_fr = 0
        self.fr_mult = 1
        self.CounterValue_Option_fr = 100000000
        self.magnitud = "1 Hz"

        # Variavles menu RCP
        self.Menu_option_RCP = 0
        self.CounterValue_RCP = 0

        # Variavles menu RCP
        self.Menu_option_LCP = 0
        self.CounterValue_LCP = 0

        # Variables menu ALC
        self.Menu_option_Ref_Clock = 0
        self.CounterValue_Ref_Clock = 0

        # Variables menu Status
        self.Menu_option_Status = 0



        self.frecuencia = 0 #rf
        self.rf_enable = 0  #enable
        self.potencia = 0   #power
        self.Att_RCP = 0 
        self.Att_LCP = 0
        
        self.ALC = "opened"
        
        
        self.ref_out_select = "100 Mhz"
        
        self.ext_ref_detect = "enable"
        self.ref_TCXO_pll = "locked"
        self.ref_VCXO_pll = "locked"
        self.ext_ref_lock_enable = "enable"
        self.ref_Coarse = "locked"
        self.fine_pll_ld = "locked"
       
        self.error = 0

        self.MAIN = "locked"
        self.rf_enable = "locked"
        self.rf1_standby = "locked"
        self.ext_ref_lock_enable = "locked"
        self.crs_ref_pll_ld = "locked"
        self.over_temp = "locked"
    
        self.Att_RCP,self.Att_LCP = self.load_variables()
       
        

        # Variables menu confirmacion:
        self.Menu_option_confirmacion = 0
        self.tipo = 0

        self.counter = 0
        self.serial = serial
        self.device = device
         # Configuración de GPIO
        GPIO.setmode(GPIO.BCM)

        
        GPIO.setup(ENCODER_PIN_A, GPIO.IN)
        GPIO.setup(ENCODER_PIN_B, GPIO.IN)
        GPIO.setup(BUTTON_PIN, GPIO.IN)

        # Configura los pines GPIO como salidas para los Atenuadores.
        for pin in gpioA1_pins:
            GPIO.setup(pin, GPIO.OUT)

        GPIO.setup(laA1_pin, GPIO.OUT)
        for pin in gpioA2_pins:
            GPIO.setup(pin, GPIO.OUT)

        GPIO.setup(laA2_pin, GPIO.OUT)

        GPIO.add_event_detect(ENCODER_PIN_A, GPIO.FALLING, callback=self.handle_encoder,bouncetime=200)
        GPIO.add_event_detect(ENCODER_PIN_B, GPIO.FALLING, callback=self.handle_encoder,bouncetime=200)
        GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, callback=self.handle_button, bouncetime=200)
        
        


        self.last_a = GPIO.input(ENCODER_PIN_A)
        self.last_b = GPIO.input(ENCODER_PIN_B)


        self.A = False
        self.B = False

        self.set_RCP(self.Att_RCP)
        self.set_LCP(self.Att_LCP)

         # Mostrar el menú cuando iniciamos el controlador
         
        self.image_path = '/home/awge/ClientEncoderAWGE/src/infrastucture/logo2.png'
        self.image_emergencia_path = '/home/awge/ClientEncoderAWGE/src/infrastucture/emergencia2.png'

        self.img_emergencia = Image.open(self.image_emergencia_path)
        self.img_emergencia = self.img_emergencia.resize((40,40), Image.LANCZOS)
        self.img_emergencia = self.img_emergencia.convert("1")

        # Invierte los colores de la imagen
        self.img_emergencia = ImageOps.invert(self.img_emergencia)



        self.display_Logo()
        # tiempo para el encendido y todas las conexiones 
        time.sleep(3)
        self.display_option()


    def display_Solv(self):
        with canvas(self.device) as draw: 
            draw.text((10, 20), "Inicializando", font=font, fill="white")
            draw.text((0,40),"Servidor conectado", font=font, fill="white")    

    def display_Emergencia(self,error):
        # Calcula el tamaño de los textos y de la imagen:
        textwidth_error = font.getlength(error)
        textwidth_title = font.getlength("ALARMA")
        imagenwidth = self.img_emergencia.width
        # Calcula las coordenadas x,centrar el texto
        x_error = (device.width - textwidth_error) // 2
        x_title = (device.width - textwidth_title) // 2
        x_imagen = (device.width - imagenwidth)//2
        if error == "OVER_TEMP" :
            with canvas(self.device) as draw: 
                draw.text((x_title, 0), "ALARMA", font=font, fill="white")
                draw.bitmap((x_imagen,10),self.img_emergencia,fill="white")
                draw.text((x_error,50),error+" "+str(self.over_temp), font=font, fill="white")
        else:
            with canvas(self.device) as draw: 
                draw.text((x_title, 0), "ALARMA", font=font, fill="white")
                draw.bitmap((x_imagen,10),self.img_emergencia,fill="white")
                draw.text((x_error,50),error, font=font, fill="white")
    
    def display_Logo(self):
        with Image.open(self.image_path) as img:
        # Es posible que desees redimensionar o adaptar la imagen al tamaño específico de tu OLED
            img = img.resize(device.size, Image.LANCZOS)
            img = img.convert("1")

            img = ImageOps.invert(img)

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
            draw.text((10, 0), "Frec:  "+self.magnitud, font=font, fill="white")
            #draw.rectangle([(7, 28), (118, 55)], outline="white")
            draw.text((10,30),"{:011}".format(self.CounterValue_Option_fr)+" Hz",font=font, fill="white")
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
    
    
    def display_option_Ref_Clock(self):
        # Calcula el tamaño de los textos y de la imagen:
        textwidth_title = font.getlength("Ref_Clock:"+self.ext_ref_lock)
        textwidth_selection = font.getlength("External   Internal")
        
        # Calcula las coordenadas x,centrar el texto
        x_title = (device.width - textwidth_title) // 2
        x_selection = (device.width - textwidth_selection) // 2

        with canvas(self.device) as draw: 
            draw.text((x_title, 0), "Ref_Clock: "+self.ext_ref_lock, font=font, fill="white")
            draw.text((x_selection,40),"External   Internal",font=font, fill="white")
            for i, option in enumerate(self.options_Ref_Clock):
                x_position = 85 - i * 55
                if i == self.Menu_option_Ref_Clock:
                    draw.text((x_position, 50), "▲" , font=font, fill="white")
                else:
                    draw.text((x_position, 50), " " , font=font, fill="white")

    def display_option_Status(self):
        value = self.format_with_spaces(self.frecuencia)
        if self.Menu_option_Status == 0:
            with canvas(self.device) as draw: 
                draw.rectangle([(0, 0), (127, 25)], outline="white")
                draw.text((10,0), "Frec. Sintetizador:  ", font=font_status, fill="white")
                draw.text((17,10),value+" Hz",font=font_status, fill="white")
                draw.text((0,26), "Main lock:", font=font_status, fill="white")
                draw.text((75,26), self.MAIN, font=font_status, fill="white")
                #draw.line([(0, 38), (128, 38)], fill="white")
                draw.text((0,38),"Ext_ref_lock:",font=font_status, fill="white")
                draw.text((75,38),self.ext_ref_lock,font=font_status, fill="white")
                #draw.line([(0, 50), (128, 50)], fill="white")
                draw.text((0,50), "Ext_ref_det:", font=font_status, fill="white")
                draw.text((75,50), self.ext_ref_detect, font=font_status, fill="white")
        elif self.Menu_option_Status == 1:
            with canvas(self.device) as draw: 
                draw.text((0, 0), "Alarmas lock", font=font_status, fill="white")
                draw.line([(0, 10), (128, 10)], fill="white")
                draw.text((0, 10), "TCXO:", font=font_status, fill="white")
                draw.text((70, 10), self.ref_TCXO_pll, font=font_status, fill="white")
                draw.text((0, 20), "VCXO:", font=font_status, fill="white")
                draw.text((70, 20), self.ref_VCXO_pll, font=font_status, fill="white")
                draw.text((0, 30), "Coarse:", font=font_status, fill="white")
                draw.text((70, 30), self.ref_Coarse, font=font_status, fill="white")
                draw.text((0, 40), "Fine:", font=font_status, fill="white")
                draw.text((70, 40), self.fine_pll_ld, font=font_status, fill="white")
                draw.text((0,50), "Main:", font=font_status, fill="white")
                draw.text((70, 50), self.MAIN, font=font_status, fill="white")
        elif self.Menu_option_Status == 2:
            with canvas(self.device) as draw:
                draw.text((0, 0), "Info device", font=font_status, fill="white")
                draw.line([(0, 10), (128, 10)], fill="white")
                draw.text((0, 10), "Att_RCP:", font=font_status, fill="white")
                draw.text((70, 10), str(self.Att_RCP)+" dB", font=font_status, fill="white")
                draw.text((0, 20), "Att_LCP:", font=font_status, fill="white")
                draw.text((70, 20), str(self.Att_LCP)+" dB", font=font_status, fill="white")
                draw.text((0, 30), "Power:", font=font_status, fill="white")
                draw.text((70, 30), str(self.potencia)+" dBm", font=font_status, fill="white")
                draw.text((0, 40), "Ref_out:", font=font_status, fill="white")
                draw.text((70, 40), self.ref_out_select, font=font_status, fill="white")
                draw.text((0, 50), "ALC:", font=font_status, fill="white")
                draw.text((70, 50), self.ALC, font=font_status, fill="white")

                
    
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
            if tipo == 4: #no indica que el cambio es de LCP
                if variable == 0 :
                    draw.text((25,12),"Ref_clock: INT",font=font, fill="white")
                    draw.text((30,40),"SI          NO",font=font, fill="white")
                    for i, option in enumerate(self.options_confirmacion):
                        x_position = 85 - i * 55
                        if i == self.Menu_option_confirmacion:
                            draw.text((x_position, 50), "▲" , font=font, fill="white")
                        else:
                            draw.text((x_position, 50), " " , font=font, fill="white")
                else:
                    draw.text((25,12),"Ref_clock: EXT",font=font, fill="white")
                    draw.text((30,40),"SI          NO",font=font, fill="white")
                    for i, option in enumerate(self.options_confirmacion):
                        x_position = 85 - i * 55
                        if i == self.Menu_option_confirmacion:
                            draw.text((x_position, 50), "▲" , font=font, fill="white")
                        else:
                            draw.text((x_position, 50), " " , font=font, fill="white")

              



    def format_with_spaces(self, n):
        s = str(n)
        parts = []
        while s:
            parts.insert(0, s[-3:])
            s = s[:-3]
        return ' '.join(parts)

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

    def next_option_Ref_Clock(self): # al ser una solucion vinaria solo hace falta un modificador para el encoder.
        self.Menu_option_Ref_Clock += 1
        if self.Menu_option_Ref_Clock > 1 :
            self.Menu_option_Ref_Clock = 0
        print("Menu_option_confirmacion: "+ str(self.Menu_option_Ref_Clock))
        self.select_option_Ref_Clock()

    def next_option_Status(self): # al ser una solucion vinaria solo hace falta un modificador para el encoder.
        self.Menu_option_Status += 1
        if self.Menu_option_Status > 2 :
            self.Menu_option_Status = 0
        print("Menu_option_Status: "+ str(self.Menu_option_Status))
        self.select_option_Status()
    
    def previous_option_Status(self):
        self.Menu_option_Status -= 1
        if self.Menu_option_Status < 0:
            self.Menu_option_Status = 2
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
        self.selected = self.options_menu[self.Menu0_option] 
        self.queue_m_c.put("get_status_cm") # se pide informacion al servidor para completar informacion.
        # la informacion se recive en la funcion run.

        
            
            

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

    def select_option_Ref_Clock(self):
        # Aquí defines lo que ocurre cuando se selecciona una opción
        #selected = self.options0[self.Menu0_option]
        # En lugar de imprimir en consola, muestra en la OLED:
        self.display_option_Ref_Clock()

    def select_option_Status(self):
        # Aquí defines lo que ocurre cuando se selecciona una opción
        #selected = self.options0[self.Menu0_option]
        # En lugar de imprimir en consola, muestra en la OLED:
        self.display_option_Status()

        
    def handle_encoder(self, channel):
        global last_interrupt_time
    
        # Verifica si la interrupción ocurrió demasiado pronto después de la anterior
        if time.time() - last_interrupt_time < DEBOUNCE_TIME:
            return
        
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
                    self.next_option_Ref_Clock()
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
                    self.next_option_Ref_Clock()
                elif self.menu == 5:
                    self.next_option_Status()
                elif self.menu == 10:
                    self.next_option_Confirmacion()
                else:
                    print("Standby")

        last_interrupt_time = time.time()  # Actualiza el tiempo de la última interrupción

        
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
        elif self.tipo == 4:
            self.display_Confirmacion(self.tipo,self.Menu_option_Ref_Clock)
            

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
                self.display_option()
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
                    self.magnitud = "1 Hz"
                    self.fr_mult = 1
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 1:
                    self.magnitud = "10 Hz"
                    self.fr_mult = 10
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 2:
                    self.magnitud = "100 Hz"
                    self.fr_mult = 100
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 3:
                    self.magnitud = "1 KHz"
                    self.fr_mult = 1000
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 4:
                    self.magnitud = "10 KHz"
                    self.fr_mult = 10000
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 5:
                    self.magnitud = "100 KHz"
                    self.fr_mult = 100000
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 6:
                    self.magnitud = "1 MHz"
                    self.fr_mult = 1000000
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 7:
                    self.magnitud = "10 MHz"
                    self.fr_mult = 10000000
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 8:
                    self.magnitud = "100 MHz"
                    self.fr_mult = 100000000
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 9:
                    self.magnitud = "1 GHz"
                    self.fr_mult = 1000000000
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 10:
                    self.magnitud = "10 GHz"
                    self.fr_mult = 10000000000
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
                self.tipo=4
                self.menu = 10
                self.menu_confirmacion()

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
                        self.queue_m_c.put("rcp="+str(self.CounterValue_RCP))
                        self.Att_RCP = self.CounterValue_RCP
                        self.set_RCP(self.CounterValue_RCP)
                        self.save_variables()
                        
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
                        self.queue_m_c.put("lcp="+str(self.CounterValue_LCP))
                        self.Att_LCP = self.CounterValue_LCP
                        self.set_LCP(self.CounterValue_LCP)
                        self.save_variables()
                        self.menu=0
                        self.display_option()
                if self.tipo == 4: # Confirmamos la configuracion de LCP
                    if self.Menu_option_confirmacion == 0 :
                        # la confirmacion es negativa por lo que salimos sin hacer nada.
                        print("modificacion de ref_clock cancelada")
                        self.menu=0
                        self.display_option()
                    else:
                        # la confirmacion es positiva por lo que tendremos que enviar el valor al servidor con la funcion set_fr = valor confirmado.
                        if self.Menu_option_Ref_Clock == 0:
                            print("ref_clock = int")
                            self.queue_m_c.put("set_ref_clock = int")
                            self.CounterValue_Ref_Clock = 0
                            self.menu=0
                            self.display_option()
                        else:
                            print("ref_clock = ext")
                            self.queue_m_c.put("set_ref_clock = ext")
                            self.CounterValue_Ref_Clock = 1
                            self.menu=0
                            self.display_option()
                

                


#---------------------------------------------------------------------------------------------------------------#
#---------------------------------------------------------------------------------------------------------------#
#---------------------------------------------    Attenuator   -------------------------------------------------#
#---------------------------------------------------------------------------------------------------------------#
#---------------------------------------------------------------------------------------------------------------#


    # Función para encender los pines GPIO de acuerdo al número binario
    def set_RCP(self,value):
        num_bits = len(gpioA1_pins)
        output = str(value)+"RCP("
    
        # Establecer cada bit en los pines GPIO y construir el string de logging
        for i in range(num_bits):
            bit = (value >> (num_bits - 1 - i)) & 1  # Invierte el orden del desplazamiento
            GPIO.output(gpioA1_pins[i], bit)
            output += str(bit)
            if i + 1 < num_bits:
                output += ","
            else:
                output += ")"
        
        print(output)  # Aquí usamos print, pero podrías usar cualquier logger que prefieras en Python
        
        time.sleep(0.1)  # Espera 100 ms
        GPIO.output(laA1_pin, GPIO.HIGH)
        time.sleep(0.1)  # Espera 100 ms
        GPIO.output(laA1_pin, GPIO.LOW)
        
        # Poner todos los pines en LOW
        for pin in gpioA1_pins:
            GPIO.output(pin, GPIO.LOW)
        time.sleep(0.1)  # Espera 100 ms
        self.queue_m_c.put("rcp = "+str(self.Att_RCP))


    def set_LCP(self,value):
        num_bits = len(gpioA2_pins)
        output = str(value)+"LCP("
        
        # Establecer cada bit en los pines GPIO y construir el string de logging
        for i in range(num_bits):
            bit = (value >> (num_bits - 1 - i)) & 1  # Invierte el orden del desplazamiento
            GPIO.output(gpioA2_pins[i], bit)
            output += str(bit)
            if i + 1 < num_bits:
                output += ","
            else:
                output += ")"
        
        print(output)  # Aquí usamos print, pero podrías usar cualquier logger que prefieras en Python
        
        time.sleep(0.1)  # Espera 100 ms
        GPIO.output(laA2_pin, GPIO.HIGH)
        time.sleep(0.1)  # Espera 100 ms
        GPIO.output(laA2_pin, GPIO.LOW)
        
        # Poner todos los pines en LOW
        for pin in gpioA2_pins:
            GPIO.output(pin, GPIO.LOW)
        time.sleep(0.1)  # Espera 100 ms
        self.queue_m_c.put("lcp = "+str(self.Att_LCP))

#---------------------------------------------------------------------------------------------------------------#
#---------------------------------------------------------------------------------------------------------------#
#-------------------------------------------    Archivo conf   -------------------------------------------------#
#---------------------------------------------------------------------------------------------------------------#
#---------------------------------------------------------------------------------------------------------------#
    def save_variables(self):
        data = {
            'RCP': self.Att_RCP,
            'LCP': self.Att_LCP
        }
        try:
            with open('/home/awge/ClientEncoderAWGE/src/infrastucture/data.json', 'w') as file:
                json.dump(data, file)
        except Exception as e:
            print(f"Error al guardar variables: {e}")

    def load_variables(self):
        filename = '/home/awge/ClientEncoderAWGE/src/infrastucture/data.json'

        if not os.path.exists(filename):
            initial_data = {
                'RCP': 0, 
                'LCP': 0
            }
            with open(filename, 'w') as file:
                json.dump(initial_data, file)
            print(f"File {filename} created with initial data.")
        
        try:
            with open('/home/awge/ClientEncoderAWGE/src/infrastucture/data.json', 'r') as file:
                data = json.load(file)
            return data['RCP'], data['LCP']
        except Exception as e:
            print(f"Error al cargar variables: {e}")

#---------------------------------------------------------------------------------------------------------------#
#---------------------------------------------------------------------------------------------------------------#
#---------------------------------------------    RUN   --------------------------------------------------------#
#---------------------------------------------------------------------------------------------------------------#
#---------------------------------------------------------------------------------------------------------------#
        
    def run(self):
        try:
            while not self.terminate_event.is_set():
            # ... tu código ...
                try:
                    valor=self.queue_c_m.get(timeout=1)
                except queue.Empty:
                    valor = "nada"
                
                if valor == "error" :
                    self.display_Emergencia("Reiniciar equipo")
                    self.menu = -2
                elif valor == "conectado":
                    self.display_option()
                    self.menu = 0
                elif valor == "get_rcp":
                    print("estoy en el menu handler")
                    self.queue_m_c.put("rcp = "+str(self.Att_RCP))
                elif valor == "get_lcp":
                    self.queue_m_c.put("lcp = "+str(self.Att_LCP))
                elif valor == "nada":
                    pass
                else:
                    data = json.loads(valor)

                    if data["x"] == "info":

                        self.frecuencia = data["rf"]
                        self.rf_enable = data["enable"] 
                        self.potencia = data["power"] 
                        self.ALC = data["ALC"] 
                        self.MAIN = data["MAIN"]
                        self.ref_out_select = data["ref_out_select"]
                        self.ext_ref_detect = data["ext_ref_detect"]
                        self.ext_ref_lock_enable = data["ext_ref_lock_enable"]
                        self.ref_TCXO_pll = data["ref_TCXO_pll"]
                        self.ref_VCXO_pll = data["ref_VCXO_pll"]
                        self.ext_ref_lock = data["ext_ref_lock"]
                        self.ref_Coarse = data["ref_Coarse"]
                        self.fine_pll_ld = data["fine_pll_ld"]

                        print("valor = "+valor)

                        if self.selected == "Frecuencia":
                            self.menu=1
                            self.CounterValue_Option_fr = self.frecuencia
                            self.select_option_Fr()
                        elif self.selected == "Att_RCP":
                            self.menu=2
                            self.CounterValue_RCP = self.Att_RCP
                            self.select_option_RCP()
                        elif self.selected == "Att_LCP":
                            self.menu=3
                            self.CounterValue_LCP = self.Att_LCP
                            self.select_option_LCP()
                        elif self.selected == "Ref_Clock":
                            self.menu=4
                            # aqui podemos modificar la variable para que cuiando entremos la flecha selectora 
                            # se ponga en la opcion actual
                            if self.ext_ref_lock == "ext":
                                self.Menu_option_Ref_Clock = 0
                            elif self.ext_ref_lock == "int":
                                self.Menu_option_Ref_Clock = 1

                            self.select_option_Ref_Clock()
                        elif self.selected == "Status":
                            self.select_option_Status()
                            self.menu=5
                        

                    elif data["x"] == "rcp":
                        self.Att_RCP = data["rcp"]
                        self.set_RCP(self.Att_RCP)
                        
                        self.save_variables()
                    
                    elif data["x"] == "lcp":
                        self.Att_RCP = data["lcp"]
                        self.set_LCP(self.Att_LCP)
                        self.save_variables()

                    elif data["x"] == "error":

                        self.error = data["error"]
                        self.rf_enable = data["rf1_out_enable"] 
                        self.rf1_standby = data["rf1_standby"]
                        self.MAIN = data["main"]
                        self.ext_ref_lock_enable = data["ref_lock_enable"]
                        self.crs_ref_pll_ld = data["crs_ref_pll_ld"]
                        self.over_temp = data["over_temp"]

     
    

                        print("error: "+str(data["error"]))

                        if self.error == 1:
                            self.device.show()
                            self.display_Emergencia("Sintetizador")
                        elif self.error == 2:
                            self.device.show()
                            self.display_Emergencia("Referencia EXT")
                        elif self.error == 3:
                            self.device.show()
                            self.display_Emergencia("Temperatura")
                        elif self.error == 4:
                            self.device.show()
                            self.display_Emergencia("RF_ENABLE:")
                        elif self.error == 5:
                            self.device.show()
                            self.display_Emergencia("RF1_STANDBY")
                        elif self.error == 0:
                            self.display_option()
                            self.menu = 0
                        elif self.error == 10:
                            self.display_Emergencia("Reiniciar equipo")
                            self.menu = -2


            # Simulando alguna operación, puedes eliminar el sleep si no lo necesitas
                pass
        except KeyboardInterrupt:
            GPIO.cleanup()
            self.terminate_event.set()
