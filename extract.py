import clr
# Подключение библиотек Autodesk Revit для работы с внутренним API программы
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *

import csv  # Модуль для экспорта структурированных данных в формат CSV
import json  # Модуль для сериализации данных в формат JSON
import os  # Модуль для проверки и создания директорий в файловой системе

# Извлечение элементов, переданных из графического интерфейса Dynamo
# Метод UnwrapElement преобразует внутренние объекты Dynamo в исходные элементы платформы Revit
walls = UnwrapElement(IN[0])

# Проверка типа входных данных: если передан одиночный элемент, он преобразуется в список
# Данная проверка обеспечивает стабильную работу цикла итерации
if not isinstance(walls, list):
    walls = [walls]

# Инициализация списков для последующего накопления извлеченных параметров
data_for_csv = []
data_for_json = []

# Определение целевой директории для сохранения результатов выгрузки
folder_path = r"E:\BIM_Data_Project1"

# Проверка наличия целевой папки на диске. Если директория отсутствует, она создается автоматически
if not os.path.exists(folder_path):
    os.makedirs(folder_path)

# Формирование полных путей к итоговым файлам экспорта данных
csv_file_path = os.path.join(folder_path, "walls_data.csv")
json_file_path = os.path.join(folder_path, "walls_data.json")


# Итерационный обход списка элементов и сбор ключевых параметров
for w in walls:
    try:
        # Извлечение уникального числового идентификатора (ID) элемента из базы данных проекта
        w_id = w.Id.Value
        # Получение наименования типа конструкции для определения марки материалов на этапе анализа
        w_name = w.Name
    
        # Поиск параметра объема поочередно для русской и английской локализаций программного комплекса
        vol_param = w.LookupParameter("Объем") or w.LookupParameter("Volume")
        
        # Если параметр существует и заполнен, считывается его строковое значение с единицами измерения (м³).
        # В случае отсутствия данных записывается нулевое значение во избежание пропусков в итоговой таблице.
        w_vol = vol_param.AsValueString() if (vol_param and vol_param.HasValue) else "0.00"
    
        # Добавление собранных параметров в массив для формирования CSV-таблицы
        data_for_csv.append([w_id, w_name, w_vol])
        
        # Формирование структуры «ключ-значение» для последующей записи в JSON
        data_for_json.append({
            "element_id": w_id,
            "element_name": w_name,
            "element_vol": w_vol
        })
    except:
        # В случае возникновения исключения (ошибки) при обработке конкретного элемента,
        # скрипт пропускает его и переходит к следующему, сохраняя общую стабильность процесса
        continue

# Запись сформированных данных в файл формата CSV
# Параметр newline='' исключает появление пустых строк при обработке в ОС Windows
with open(csv_file_path, mode='w', encoding='utf-8', newline='') as csv_file:
    # Установка точки с запятой в качестве разделителя для корректного считывания библиотекой Pandas
    writer = csv.writer(csv_file, delimiter=';')
    # Запись строки заголовков таблицы
    writer.writerow(['element_id', 'element_name', 'element_vol'])
    # Запись всех накопленных строк с параметрами элементов
    writer.writerows(data_for_csv)
    
# Запись сформированных данных в файл формата JSON
with open(json_file_path, mode='w', encoding='utf-8') as json_file:
    # Параметр ensure_ascii=False сохраняет кириллические символы в исходном виде,
    # а indent=4 структурирует код для удобства визуального контроля
    json.dump(data_for_json, json_file, ensure_ascii=False, indent=4)
    

# Передача итоговой информации о количестве обработанных строк в выходной порт Dynamo
OUT = f"Файлы созданы. Всего строк: {len(data_for_csv)}"
