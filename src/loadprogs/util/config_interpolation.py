import configparser
import os


class ExtendedEnvInterpolation(configparser.ExtendedInterpolation):
    """Interpolation which expands environment variables in values."""

    def before_get(self, parser, section, option, value, defaults):
        value = os.path.expandvars(value)
        return super().before_get(parser, section, option, value, defaults)
