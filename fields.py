# -*- coding: utf-8 -*-
import datetime
import logging
from custom_erros import ValidationError

UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


class Field:
    _type = None

    def __init__(self, required, nullable=False):
        self.required = required
        self.nullable = nullable
        self._name = None

    def __get__(self, instance, owner):
        return self._name

    def __set_name__(self, owner, name):
        self._name = name

    def __set__(self, owner, value):
        if value is None and (self.required or not self.nullable):
            raise ValidationError(
                f'{self.__class__.__name__} is required and not nullable')
        elif value is None and self.nullable:
            self._name = value
        else:
            if isinstance(value, self._type):
                self.validate(value)
                self._name = value
            else:
                raise ValidationError(
                    f'{self.__class__.__name__} must be {self._type}, '
                    f'but {type(value).__name__} received')

    def validate(self, value):
        pass


class CharField(Field):
    _type = str


class ArgumentsField(Field):
    _type = dict


class EmailField(CharField):

    def validate(self, value):
        if '@' in value:
            return
        else:
            raise ValidationError(f'{self.__class__.__name__} must be contains "@')


class PhoneField(Field):
    _type = (int, str)

    def validate(self, value):
        value = str(value)
        if not value:
            pass
        elif len(value) != 11:
            raise ValidationError('PhoneField must contain 11 numbers')
        elif not value.isdigit():
            raise ValidationError('PhoneField must contain only digits')
        elif not value.startswith('7'):
            raise ValidationError('PhoneField must starts with "7"')


class DateField(CharField):

    def validate(self, value):
        try:
            datetime.datetime.strptime(value, '%d.%m.%Y')
        except Exception as e:
            # logging.info(e)
            raise ValidationError("DateField is incorrect")


class BirthDayField(DateField):

    def validate(self, value):
        super().validate(value)
        value = str(value)
        birthday_year = datetime.datetime.strptime(value, '%d.%m.%Y').year
        now_year = datetime.datetime.now().year
        if (now_year - birthday_year) > 70:
            raise ValidationError('More than 70 yeas have been since date of birth')


class GenderField(Field):
    _type = int

    def validate(self, value):
        if value not in GENDERS:
            raise ValidationError(
                'Wrong value for GenderField, permissible value in [0, 1, 2]')


class ClientIDsField(Field):
    _type = list

    def validate(self, value):
        all_is_int = all([type(i) is int for i in value]) if value else False
        if not all_is_int:
            raise ValidationError('ClientIDsField must contains only int items')
