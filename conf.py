import os
import configparser


PATH = os.getcwd() + "./config/config.ini"

#   получаем настройки
def get_configuration():
    config = configparser.ConfigParser()
    try:
        config.read(PATH)
        return config["DEFAULT"]
    except IOError as e:
        print("Файл конфигурации не найден...")


def write_configuration(login, password):
    config = configparser.ConfigParser()
    with open(PATH, 'w') as file:
        config.set("DEFAULT", "login", login)
        config.set("DEFAULT", "password", password)
        config.write(file) 