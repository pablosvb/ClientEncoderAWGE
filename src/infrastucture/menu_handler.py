import threading
import time
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import sh1106
from PIL import ImageFont, ImageDraw
import RPi.GPIO as GPIO
import src.domain.GPIOConstants as GC

# Cargar una fuente TrueType y ajustar su tamaño
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # Ruta a una fuente ttf en tu sistema, ajusta si es necesario
font_size = 11
font = ImageFont.truetype(font_path, font_size)

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

class MenuHandler:

    def __init__(self):
        self.options_menu = ["Frecuencia", "Att_RCP", "Att_LCP", "ALC_Mode", "Status"]
        self.options_frecuencia = [0,0,0,0,0,0,0,0,0,0,0]
        self.num = 0
        self.menu = 0
        self.Menu0_option = 0
        self.Menu_Option_fr = 0
        self.fr_mult = 1
        self.CounterValue_Option_fr = 0
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
        self.display_option()

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
            for i, option in enumerate(self.options_frecuencia):
                x_position = i * 12
                if i == self.Menu0_option:
                    draw.text((x_position, 60), "▲" , font=font, fill="white")
                else:
                    draw.text((x_position, 60), " " , font=font, fill="white")
                


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
        self.Menu_Option_fr += 1
        if self.Menu_Option_fr == len(self.options_frecuencia):
            self.Menu_Option_fr = 0
        if self.CounterValue_Option_fr == 20000000000 :
            self.CounterValue_Option_fr = 0
        print("Menu_opcion_fr: "+self.Menu_Option_fr + " value fr: "+"{:011}".format(self.CounterValue_Option_fr)+"Hz")
        self.display_option_frecuencia()

    def previous_option_Fr(self):
        self.CounterValue_Option_fr -= 1 * self.fr_mult
        self.Menu_Option_fr -= 1
        if self.Menu_Option_fr < 0:
            self.Menu_Option_fr = len(self.options_frecuencia) - 1
        if self.CounterValue_Option_fr < 0:
            self.CounterValue_Option_fr = 20000000000
        print("Menu_opcion_fr: "+self.Menu_Option_fr + " value fr: "+"{:011}".format(self.CounterValue_Option_fr)+"Hz")
        self.display_option_frecuencia()


    def select_option(self):
        # Aquí defines lo que ocurre cuando se selecciona una opción
        selected = self.options_menu[self.Menu_Option_fr]
        # En lugar de imprimir en consola, muestra en la OLED:
        with canvas(self.device) as draw:
            draw.text((0, 0), f"Config {selected}", font=font, fill="white")
            self.menu=1

    def select_option_Fr(self):
        # Aquí defines lo que ocurre cuando se selecciona una opción
        #selected = self.options0[self.Menu0_option]
        # En lugar de imprimir en consola, muestra en la OLED:
        with canvas(self.device) as draw:
            draw.text((0, 0), f"Frequency:", font=font, fill="white")
            draw.text((0,50),"{:011}".format(self.Menu_Option_fr)+"Hz")
            

        
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

        else:
            print(f"-  : {current_a}   {current_b}")
            if current_a != current_b:
                if self.menu == 0:
                    self.previous_option()
                elif self.menu == 1:
                    self.previous_option_Fr()
        
        

    def handle_button(self, channel):
        start_time = time.time()
        #print(len(self.options0))
        while GPIO.input(BUTTON_PIN) == 0:  # Esperar mientras esté presionado
            time.sleep(0.01)
            
        end_time = time.time()
        if (end_time - start_time) > 2:  # Si se presionó más de 2 segundos
            self.pulsado_Atras = True
            
        else:
            if self.menu == 0:
                self.select_option()
            elif self.menu == 1:
                # ahora entramos en las opciones que hace el boton en este menu de Frecuencia:
                # y lo que hacemos es que cada vez que pulsemos generaremos un multiplicador por 10 hasta llegar a Gz que es 10*10 a 9
                # Este es el de hz x 1 
                if self.Menu_Option_fr == 0:
                    self.fr_mult = 1
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 1:
                    self.fr_mult = 10
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 2:
                    self.fr_mult = 100
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 3:
                    self.fr_mult = 1000
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 4:
                    self.fr_mult = 10000
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 5:
                    self.fr_mult = 100000
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 6:
                    self.fr_mult = 1000000
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 7:
                    self.fr_mult = 10000000
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 8:
                    self.fr_mult = 10000000
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 9:
                    self.fr_mult = 100000000
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 10:
                    self.fr_mult = 1000000000
                    self.select_option_Fr()
                elif self.Menu_Option_fr == 11:
                    self.fr_mult = 1000000000
                    self.select_option_Fr()
                    
                            # aceptaremos lo que tengamos en el menu.


    def run(self):
        current_val = 0
        while True:
            try:
                while True:
                    pass
        
            except KeyboardInterrupt:
                GPIO.cleanup()