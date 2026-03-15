from .keys.key import environment


log_config = {
    "include_extra_info": False,
    "write_to_file": False,
    "log_level": "DEBUG" if environment == "development" else "INFO",
}
