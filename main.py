import sys
from io import StringIO
import json
from sqlalchemy import create_engine
import pandas as pd
import ollama  # Наша локальная нейросеть

# 1. НАСТРОЙКА ОТОБРАЖЕНИЯ ТАБЛИЦ В КОНСОЛИ
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

# 2. ЗАГРУЗКА И СЧИТЫВАНИЕ CSV-ФАЙЛА
csv_path = r"E:\BIM_Data_Project1\walls_data.csv"
df = pd.read_csv(csv_path, sep=';')

# 3. ОЧИСТКА ДАННЫХ И ПРИВЕДЕНИЕ ТИПОВ
df['clean_vol'] = df['element_vol'].str.replace('м³', '').str.replace(',', '.').astype(float)

# 4. ФУНКЦИЯ ДЛЯ СТОИМОСТИ БЕТОНА
def get_price_per_m3(name):
    if 'В30' in str(name):    
        return 6500.0
    if 'В25' in str(name):    
        return 5800.0
    return 5000.0

# Добавляем цену за куб и считаем стоимость для каждой стены
df['price_per_m3'] = df['element_name'].apply(get_price_per_m3)
df['total_wall_cost'] = df['clean_vol'] * df['price_per_m3'].round(2)


# --- ТАБЛИЦЫ ДЛЯ АНАЛИЗА ---
# 1. Детальная таблица по всем 671 стенам
detailed_walls_df = df[['element_id', 'element_name', 'clean_vol', 'price_per_m3', 'total_wall_cost']].copy()
detailed_walls_df.columns = ['ID элемента', 'Марка бетона', 'Объем стены м³', 'Цена за м³ руб', 'Итоговая стоимость стены руб']

# 2. Сводные метрики (сгруппированные данные)
grouped = df.groupby('element_name')
metrics_df = grouped.agg(
    total_count=('element_id', 'count'),
    total_volume=('clean_vol', 'sum'),
    avg_volume=('clean_vol', 'mean'),
    concrete_price_m3=('price_per_m3', 'first'),
    total_cost_rub=('total_wall_cost', 'sum'),
    min_wall_cost_rub=('total_wall_cost', 'min'),
    max_wall_cost_rub=('total_wall_cost', 'max')
).reset_index()

metrics_df.columns = [
    'Имя элемента', 'Кол-во стен', 'Общая сумма м³', 'Средний объем м³', 
    'Цена бетона за м³', 'Суммарная стоимость руб', 'Стоимость мин стены руб', 'Стоимость макс стены руб'
]


# --- AGENTIC AI: ФУНКЦИЯ ВЫПОЛНЕНИЯ PYTHON-КОДА ---
def execute_python_code(code_string):
    # Перенаправляем вывод print в строку, чтобы перехватить результат выполнения
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    
    # Даем модели доступ к контексту твоих датафреймов
    local_vars = {
        'df': df,
        'detailed_walls_df': detailed_walls_df,
        'metrics_df': metrics_df
    }
    
    try:
        exec(code_string, {}, local_vars)
        sys.stdout = old_stdout
        return redirected_output.getvalue().strip()
    except Exception as e:
        sys.stdout = old_stdout
        return f"Ошибка при выполнении кода: {e}"


# --- НАСТРОЙКА ИНСТРУКЦИЙ ДЛЯ ИИ-АГЕНТА ---
system_prompt = """
Ты — ИИ-Агент, продвинутый аналитик BIM-данных и сметной стоимости.
У тебя есть доступ к трем датафреймам Pandas:
1. `df` - исходные данные стен из Revit.
2. `detailed_walls_df` - детальная таблица (колонки: 'ID элемента', 'Марка бетона', 'Объем стены м³', 'Цена за м³ руб', 'Итоговая стоимость стены руб').
3. `metrics_df` - сводная таблица по маркам (колонки: 'Имя элемента', 'Кол-во стен', 'Общая сумма м³', 'Средний объем м³', 'Цена бетона за м³', 'Суммарная стоимость руб', 'Стоимость мин стены руб', 'Стоимость макс стены руб').

ПРАВИЛО РАБОТЫ:
Ты физически НЕ умеешь считать сам. Если пользователь просит что-то посчитать, узнать сумму, среднее, количество или найти строку — ты ОБЯЗАН написать Python-код, который выведет ответ через print().
Твой ответ должен состоять СТРОГО ИЗ ДВУХ ЧАСТЕЙ:
1. Краткое текстовое рассуждение (что ты хочешь посчитать).
2. Блок кода в тегах ```python ... ```, который решает задачу. Код должен обязательно использовать функцию print() для вывода финального результата!

Пример твоего ответа:
Чтобы узнать общую стоимость, нужно просуммировать колонку 'Суммарная стоимость руб' в metrics_df.
```python
print(metrics_df['Суммарная стоимость руб'].sum())
```
"""

print("\n" + "="*60)
print(" 🚀 AGENTIC AI ЗАПУЩЕН НА RTX 3070 (БЕЗ ОШИБОК В ИМПОРТАХ)!")
print(" Теперь модель будет писать Python-код для точных расчетов.")
print(" Чтобы завершить общение, напишите: выход")
print("="*60 + "\n")

chat_history = [{'role': 'system', 'content': system_prompt}]

# --- ЦИКЛ БЕСКОНЕЧНОГО ДИАЛОГА (ЧИСТЫЙ КРАСИВЫЙ ВЫВОД) ---
while True:
    user_input = input("Вы: ")
    if user_input.lower().strip() in ['выход', 'exit', 'quit', 'стоп']:
        print("\nДиалог завершен. До связи!")
        break
    if not user_input.strip():
        continue
        
    chat_history.append({'role': 'user', 'content': user_input})
    print("Робот думает...", end="\(\r\)") # Эффект загрузки в одной строке
    
    try:
        # 1. Запрашиваем код у ИИ
        response = ollama.chat(
            model='qwen2.5:3b',
            messages=chat_history,
            options={'temperature': 0.1}
        )
        ai_raw_response = response['message']['content']
        
        if "```python" in ai_raw_response:
            # Молча извлекаем и выполняем код без вывода лишнего лога в консоль
            code_block = ai_raw_response.split("```python")[1].split("```")[0].strip()
            execution_result = execute_python_code(code_block)
            
            # Передаем результат обратно модели и просим сделать чистый ответ без markdown
            chat_history.append({'role': 'assistant', 'content': ai_raw_response})
            chat_history.append({
                'role': 'user', 
                'content': f"Код выполнен. Результат: {execution_result}. Ответь пользователю человеческим языком. ПРАВИЛО: Не используй markdown-разметку (никаких звездочек ** и решеток #), пиши чистым текстом."
            })
            
            final_response = ollama.chat(
                model='qwen2.5:3b',
                messages=chat_history,
                options={'temperature': 0.2}
            )
            
            # Очищаем строку "Робот думает..." и выводим только чистый ответ
            print(" " * 20, end="\r")
            print(f"Ответ ИИ: {final_response['message']['content']}")
            print("-" * 50)
            chat_history.append({'role': 'assistant', 'content': final_response['message']['content']})
            
        else:
            # Если код не генерировался, просто выводим текст (но тоже просим почистить от markdown, если он там есть)
            clean_text = ai_raw_response.replace("**", "").replace("#", "")
            print(" " * 20, end="\r")
            print(f"Ответ ИИ: {clean_text}")
            print("-" * 50)
            chat_history.append({'role': 'assistant', 'content': clean_text})
            
    except Exception as e:
        print(f"\n[ОШИБКА]: {e}\n")
