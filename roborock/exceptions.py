"""Roborock exceptions."""


class RoborockException(Exception):
    """Class for Roborock exceptions."""


class RoborockTimeout(RoborockException):
    """Class for Roborock timeout exceptions."""


class RoborockConnectionException(RoborockException):
    """Class for Roborock connection exceptions."""


class RoborockBackoffException(RoborockException):
    """Class for Roborock exceptions when many retries were made."""


class VacuumError(RoborockException):
    """Class for vacuum errors."""

    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__()

    def __str__(self, *args, **kwargs):  # real signature unknown
        """Return str(self)."""
        return f"{self.code}: {self.message}"


class CommandVacuumError(RoborockException):
    """Class for command vacuum errors."""

    def __init__(self, command: str, vacuum_error: VacuumError):
        self.message = f"{command}: {str(vacuum_error)}"
        super().__init__(self.message)


class RoborockAccountDoesNotExist(RoborockException):
    """Class for Roborock account does not exist exceptions."""


class RoborockUrlException(RoborockException):
    """Class for being unable to get the URL for the Roborock account."""


class RoborockInvalidCode(RoborockException):
    """Class for Roborock invalid code exceptions."""


class RoborockInvalidEmail(RoborockException):
    """Class for Roborock invalid formatted email exceptions."""


class RoborockInvalidUserAgreement(RoborockException):
    """Class for Roborock invalid user agreement exceptions."""


class RoborockNoUserAgreement(RoborockException):
    """Class for Roborock no user agreement exceptions."""
