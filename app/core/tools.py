from sqlalchemy import Boolean, Enum, Integer, Float, String
from sqlalchemy.orm.attributes import InstrumentedAttribute
from app.core.errors import ErrorCode
from app.schemas.base import BizException

def str_to_bool(val):
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        if val.lower() == "true":
            return True
        if val.lower() == "false":
            return False
    return val

def str_to_enum(val, enum_cls):
    if isinstance(val, enum_cls):
        return val
    if isinstance(val, str):
        try:
            return enum_cls(val)
        except ValueError:
            raise BizException(code=ErrorCode.PROPERTY_ERROR, message=f"{val} 不是合法的 {enum_cls.__name__} 枚举值")
    return val

def auto_cast_fields(subclass, data: dict):
    """
    根据 SQLAlchemy 子类模型的字段类型自动转换 data 字段的类型
    """
    for field, value in data.items():
        # 只处理模型里有的字段
        if not hasattr(subclass, field):
            continue
        column = getattr(subclass, field)
        if not isinstance(column, InstrumentedAttribute):
            continue
        column_type = column.property.columns[0].type

        # Boolean
        if isinstance(column_type, Boolean):
            data[field] = str_to_bool(value)
        # Enum
        elif isinstance(column_type, Enum):
            enum_cls = column_type.enum_class
            data[field] = str_to_enum(value, enum_cls)
        # Integer
        elif isinstance(column_type, Integer):
            if value is not None and not isinstance(value, int):
                try:
                    data[field] = int(value)
                except Exception:
                    raise BizException(code=ErrorCode.PROPERTY_ERROR, message=f"{field} 字段无法转换为 int: {value}")
        # Float
        elif isinstance(column_type, Float):
            if value is not None and not isinstance(value, float):
                try:
                    data[field] = float(value)
                except Exception:
                    raise BizException(code=ErrorCode.PROPERTY_ERROR, message=f"{field} 字段无法转换为 float: {value}")
        # String
        elif isinstance(column_type, String):
            if value is not None and not isinstance(value, str):
                data[field] = str(value)
        # 其他类型可按需扩展
    return data