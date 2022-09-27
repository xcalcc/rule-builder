class LangNotSupported(Exception):
    def __init__(self, message="Your input language is not supported"):
        self.message = "LangNotSupported : "+message
        super().__init__(self.message)

class LangNotProvided(Exception):
    def __init__(self, message="You haven't given the target language"):
        self.message = "LangNotProvided: "+message
        super().__init__(self.message)
