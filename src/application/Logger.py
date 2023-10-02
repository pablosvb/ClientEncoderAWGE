import logging

class Logger:
    def __init__(self, log_file='ClienteENCODER.log', log_level_console=logging.DEBUG, log_level_file=logging.DEBUG):
        # Crear un logger específico para la clase
        self.logger = logging.getLogger(__name__)
        
        # Evitar la adición duplicada de handlers
        if not self.logger.handlers:
            self.logger.setLevel(logging.DEBUG)  # Nivel base para el logger

            # Configurar el formato de los registros
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

            # Configurar registro en consola
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            console_handler.setLevel(log_level_console)
            self.logger.addHandler(console_handler)

            # Configurar registro en archivo
            file_handler = logging.FileHandler(log_file, mode='a')
            file_handler.setFormatter(formatter)
            file_handler.setLevel(log_level_file)
            self.logger.addHandler(file_handler)

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)
