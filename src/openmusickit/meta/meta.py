class FrozenMeta(type):
    def __setattr__(cls, name, value):
        if "system" in name.lower():
            raise AttributeError(
                f"'{name}' is system-related metadata and cannot be modified."
            )
        super().__setattr__(name, value)