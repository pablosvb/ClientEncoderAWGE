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
        self.options0 = ["Frecuencia", "Att_RCP", "Att_LCP", "ALC_Mode", "Status"]
        self.options1 = [0,0,0,0,0,0,0,0,0,0,0]
        self.num = 0
        self.Menu0_option = 0
        self.Menu1_Option = 0
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

    def display_option(self):
        with canvas(self.device) as draw: 
            for i, option in enumerate(self.options0):
                y_position = i * 12
                if i == self.Menu0_option:
                    draw.text((0, y_position), "▶ " + option, font=font, fill="white")
                    print(f"-> {option}")
                else:
                    draw.text((0, y_position), "   " + option, font=font, fill="white")
                    print(f"   {option}")
    
    def display_option_lateral(self):
        with canvas(self.device) as draw: 
            for i, option in enumerate(self.options1):
                x_position = i * 12
                if i == self.Menu0_option:
                    draw.text((x_position, 40), "▲" + option, font=font, fill="white")
                    print(f"-> {option}")
                else:
                    draw.text((x_position, 40), " " + option, font=font, fill="white")
                    print(f"   {option}")


    def next_option(self):
        self.Menu0_option += 1
        if self.Menu0_option == len(self.options0):
            self.Menu0_option = 0
        print(self.Menu0_option)
        self.display_option()

    def previous_option(self):
        self.Menu0_option -= 1
        
        if self.Menu0_option < 0:
            self.Menu0_option = len(self.options0) - 1
        print(self.Menu0_option)
        self.display_option()

    def next_option2(self):
        self.Menu1_Option += 1
        if self.Menu1_Option == len(self.options1):
            self.Menu1_Option = 0
        print(self.Menu1_Option)
        self.display_option_lateral()

    def previous_option2(self):
        self.Menu1_Option -= 1
        if self.Menu1_Option < 0:
            self.Menu1_Option = len(self.options1) - 1
        print(self.Menu1_Option)
        self.display_option_lateral()

    def next_mas(self):
        self.num += 1
        if self.num == 10:
            self.num = 0
        print(self.num)
        self.options1[self.Menu1_Option] = self.num
        self.display_option()

    def previous_menos(self):
        self.num -= 1
        if self.num < 0:
            self.num =  9
        print(self.num)
        self.options1[self.Menu1_Option] = self.num
        self.display_option()

    def select_option(self):
        # Aquí defines lo que ocurre cuando se selecciona una opción
        selected = self.options0[self.current_option]
        # En lugar de imprimir en consola, muestra en la OLED:
        with canvas(self.device) as draw:
            draw.text((0, 0), f"Config {selected}", font=font, fill="white")
        self.display_option()
        
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
                    self.next_option2()
                elif self.menu == 2:
                    self.next_mas()

        else:
            print(f"-  : {current_a}   {current_b}")
            if current_a != current_b:
                if self.menu == 0:
                    self.previous_option()
                elif self.menu == 1:
                    self.previous_option2()
                elif self.menu == 2:
                    self.previous_menos()
        
        

    def handle_button(self, channel):
        start_time = time.time()
        print(len(self.options0))
        while GPIO.input(BUTTON_PIN) == 0:  # Esperar mientras esté presionado
            time.sleep(0.01)
            
        end_time = time.time()
        if (end_time - start_time) > 2:  # Si se presionó más de 2 segundos
            self.pulsado_Atras = True
            self.menu -=1 
            if self.menu == -1:
                device.hide()
        else:
            self.menu +=1
            if self.menu == 0: # estaría la pantalla apagada y la encenderiamos
                self.show()
            else:
                if self.menu == 0 : # Estariamos en el menu principal y accederiamos a los primeros submenus
                    self.select_option()
                elif self.menu == 1 :
                                    # aceptaremos lo que tengamos en el menu.


    def run(self):
       
        current_val = 0
        while True:
            try:
                while True:
                    pass
        
            except KeyboardInterrupt:
                GPIO.cleanup()