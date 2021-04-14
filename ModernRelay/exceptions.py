class DeliveryAgentException(Exception):
    def __init__(self, message):
        self.message = message


class ConfigParsingException(Exception):
    def __init__(self, message):
        self.message = message
