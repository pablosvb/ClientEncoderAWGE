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

class MenuHandler:

    def __init__(self):
        self.options = ["Frecuencia", "Att_RCP", "Att_LCP", "ALC_Mode", "Status"]
        self.current_option = 0
        self.counter = 0
        self.serial = serial
        self.device = device
         # Configuración de GPIO
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
            for i, option in enumerate(self.options):
                y_position = i * 12
                if i == self.current_option:
                    draw.text((0, y_position), "▶ " + option, font=font, fill="white")
                    print(f"-> {option}")
                else:
                    draw.text((0, y_position), "   " + option, font=font, fill="white")
                    print(f"   {option}")

    def next_option(self):
        self.current_option += 1
        if self.current_option == len(self.options):
            self.current_option = 0
        print(self.current_option)
        self.display_option()

    def previous_option(self):
        self.current_option -= 1
        
        if self.current_option < 0:
            self.current_option = len(self.options) - 1
        print(self.current_option)
        self.display_option()

    def select_option(self):
        # Aquí defines lo que ocurre cuando se selecciona una opción
        selected = self.options[self.current_option]
        # En lugar de imprimir en consola, muestra en la OLED:
        with canvas(self.device) as draw:
            draw.text((0, 0), f"Config {selected}...", font=font, fill="white")
        time.sleep(2)  # Mostrar mensaje por 2 segundos, puedes ajustar
        self.display_option()
        
    def handle_encoder(self, channel):
        print(channel)

        current_a = GPIO.input(ENCODER_PIN_A)
        current_b = GPIO.input(ENCODER_PIN_B)

        
        
        if channel == ENCODER_PIN_A:
            print(f"+  : {current_a}   {current_b}")
            if current_b != current_a:
                self.next_option()
        else:
            print(f"-  : {current_a}   {current_b}")
            if current_a != current_b:
                self.previous_option()
        
        

    def handle_button(self, channel):
        start_time = time.time()
        print(len(self.options))
        while GPIO.input(BUTTON_PIN) == 0:  # Esperar mientras esté presionado
            time.sleep(0.01)
            
        end_time = time.time()
        if (end_time - start_time) > 2:  # Si se presionó más de 2 segundos
            # Aquí puedes manejar el evento de presionar el botón por mucho tiempo
            return
        
        self.select_option()

    def run(self):
       
        current_val = 0
        while True:
            try:
                while True:
                    pass
        
            except KeyboardInterrupt:
                GPIO.cleanup()