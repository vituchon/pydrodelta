from pandas import DataFrame

class DataFrameDescriptor:
    """DataFrame descriptor with default None"""
    def __set_name__(self, owner, name):
        self._name = name

    def __get__(self, instance, owner):
        return instance.__dict__[self._name]

    def __set__(self, instance, value):
        try:
            instance.__dict__[self._name] = value if isinstance(value,DataFrame) else DataFrame(value) if value is not None else None
        except ValueError:
            raise ValueError(f'"{self._name}" must be a DataFrame or a DataFrame-coercible type') from None
