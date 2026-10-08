# Практическое руководство по основам Bash-скриптинга для Linux

## 1. Введение в Bash-скрипты

### Что такое Bash-скрипт?
Bash-скрипт - это текстовый файл, содержащий последовательность команд для оболочки Bash.

### Преимущества использования скриптов:
- Автоматизация повторяющихся задач
- Экономия времени
- Снижение вероятности ошибок
- Воспроизводимость действий

## 2. Создание первого скрипта

### Шаг 1: Создание файла
```bash
nano first_script.sh
```

### Шаг 2: Добавление "шебанга" (shebang)
```bash
#!/bin/bash
# Это комментарий - первая строка должна указывать на интерпретатор
```

### Шаг 3: Простой скрипт
```bash
#!/bin/bash
echo "Привет, мир!"
echo "Текущая дата: $(date)"
echo "Текущий пользователь: $USER"
```

### Шаг 4: Даем права на выполнение
```bash
chmod +x first_script.sh
```

### Шаг 5: Запуск скрипта
```bash
./first_script.sh
```

## 3. Основы синтаксиса

### Переменные
```bash
#!/bin/bash
# Объявление переменных
NAME="Иван"
AGE=25
SCRIPT_DIR=$(pwd)

# Использование переменных
echo "Имя: $NAME"
echo "Возраст: $AGE"
echo "Директория: $SCRIPT_DIR"

# Переменные окружения
echo "Домашняя директория: $HOME"
echo "Текущая оболочка: $SHELL"
```

### Ввод данных
```bash
#!/bin/bash
echo "Введите ваше имя:"
read USERNAME
echo "Привет, $USERNAME!"

# Чтение без промпта
read -p "Введите ваш возраст: " AGE
echo "Вам $AGE лет"

# Скрытый ввод (для паролей)
read -s -p "Введите пароль: " PASSWORD
echo
echo "Пароль принят"
```

## 4. Условные операторы

### Базовый синтаксис if
```bash
#!/bin/bash
read -p "Введите число: " NUMBER

if [ $NUMBER -gt 10 ]; then
    echo "Число больше 10"
elif [ $NUMBER -eq 10 ]; then
    echo "Число равно 10"
else
    echo "Число меньше 10"
fi
```

### Операторы сравнения:
- **Числа**: `-eq`, `-ne`, `-gt`, `-lt`, `-ge`, `-le`
- **Строки**: `=`, `!=`, `-z` (пустая), `-n` (не пустая)
- **Файлы**: `-f` (существует файл), `-d` (существует директория), `-r` (доступен для чтения)

### Пример проверки файла
```bash
#!/bin/bash
FILE="/etc/passwd"

if [ -f "$FILE" ]; then
    echo "Файл $FILE существует"
    if [ -r "$FILE" ]; then
        echo "Файл доступен для чтения"
    fi
else
    echo "Файл не существует"
fi
```

## 5. Циклы

### Цикл for
```bash
#!/bin/bash
# Простой цикл
for i in 1 2 3 4 5; do
    echo "Итерация: $i"
done

# Цикл по файлам
for file in *.txt; do
    echo "Обрабатываю файл: $file"
done

# Цикл с диапазоном
for i in {1..5}; do
    echo "Число: $i"
done
```

### Цикл while
```bash
#!/bin/bash
# Чтение файла построчно
while read line; do
    echo "Строка: $line"
done < /etc/passwd

# Цикл с условием
COUNT=1
while [ $COUNT -le 5 ]; do
    echo "Счетчик: $COUNT"
    ((COUNT++))
done
```

## 6. Функции

### Создание и использование функций
```bash
#!/bin/bash
# Определение функции
greet_user() {
    local name=$1
    echo "Привет, $name!"
    return 0
}

# Функция с возвращаемым значением
check_file() {
    if [ -f "$1" ]; then
        return 0
    else
        return 1
    fi
}

# Вызов функций
greet_user "Анна"

if check_file "/etc/hosts"; then
    echo "Файл существует"
else
    echo "Файл не найден"
fi
```

## 7. Полезные примеры для Kali Linux/Ubuntu

### Сканер сети
```bash
#!/bin/bash
# Простой сканер портов
TARGET="192.168.1.1"

echo "Сканирование портов на $TARGET"
for port in 22 80 443 8080; do
    nc -z -w 1 $TARGET $port 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "Порт $port открыт"
    fi
done
```

### Мониторинг системы
```bash
#!/bin/bash
# Мониторинг ресурсов системы
echo "=== Мониторинг системы ==="
echo "Дата: $(date)"
echo "Загрузка CPU: $(uptime | awk '{print $10 $11 $12}')"
echo "Свободная память: $(free -h | grep Mem | awk '{print $4}')"
echo "Дисковое пространство:"
df -h / | tail -1
```

### Резервное копирование
```bash
#!/bin/bash
# Простой скрипт бэкапа
BACKUP_DIR="/home/backup"
SOURCE_DIR="/home/user/documents"
DATE=$(date +%Y-%m-%d)

if [ ! -d "$BACKUP_DIR" ]; then
    mkdir -p "$BACKUP_DIR"
fi

tar -czf "$BACKUP_DIR/backup_$DATE.tar.gz" "$SOURCE_DIR"
echo "Бэкап создан: $BACKUP_DIR/backup_$DATE.tar.gz"
```

### Автоматизация обновлений
```bash
#!/bin/bash
# Скрипт для автоматического обновления системы
echo "Начало обновления системы: $(date)"

# Для Ubuntu
sudo apt update && sudo apt upgrade -y

# Для Kali Linux (раскомментировать если нужно)
# sudo apt update && sudo apt full-upgrade -y

echo "Обновление завершено: $(date)"
```

## 8. Обработка ошибок

### Базовая обработка ошибок
```bash
#!/bin/bash
# Выход при ошибке
set -e

# Проверка прав администратора
if [ "$EUID" -ne 0 ]; then
    echo "Для выполнения скрипта требуются права root"
    exit 1
fi

# Логирование ошибок
exec 2> error.log

# Пример с обработкой ошибок команды
cp important_file.txt backup/ || {
    echo "Ошибка копирования файла"
    exit 1
}
```

## 9. Отладка скриптов

### Методы отладки
```bash
#!/bin/bash
# Включение отладки
set -x  # Показывает выполняемые команды
set -e  # Выход при первой ошибке
set -u  # Выход при использовании необъявленных переменных

# Ваш код здесь

# Выключение отладки
set +x
```

### Запуск с отладкой
```bash
bash -x your_script.sh
```

## 10. Лучшие практики

1. **Всегда используйте shebang**
2. **Комментируйте код**
3. **Проверяйте существование файлов**
4. **Обрабатывайте ошибки**
5. **Используйте осмысленные имена переменных**
6. **Тестируйте скрипты в безопасной среде**
7. **Следите за правами доступа**

### Пример хорошо оформленного скрипта
```bash
#!/bin/bash
#
# Скрипт для создания резервных копий
# Автор: Ваше Имя
# Дата: 2024

set -euo pipefail

readonly BACKUP_DIR="/var/backups"
readonly SOURCE_DIRS=("/home" "/etc")
readonly DATE=$(date +%Y%m%d_%H%M%S)

main() {
    check_privileges
    create_backup_dir
    perform_backup
    cleanup_old_backups
}

check_privileges() {
    if [[ $EUID -ne 0 ]]; then
        echo "Ошибка: Скрипт должен запускаться с правами root" >&2
        exit 1
    fi
}

create_backup_dir() {
    if [[ ! -d "$BACKUP_DIR" ]]; then
        mkdir -p "$BACKUP_DIR"
    fi
}

perform_backup() {
    local backup_file="$BACKUP_DIR/backup_$DATE.tar.gz"
    
    if tar -czf "$backup_file" "${SOURCE_DIRS[@]}" 2>/dev/null; then
        echo "Резервная копия создана: $backup_file"
    else
        echo "Ошибка создания резервной копии" >&2
        exit 1
    fi
}

cleanup_old_backups() {
    find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +7 -delete
}

main "$@"
```

## 11. Полезные команды для скриптов

- `grep` - поиск текста
- `awk`, `sed` - обработка текста
- `find` - поиск файлов
- `curl`, `wget` - работа с сетью
- `cron` - планировщик задач

Это руководство покрывает основные аспекты Bash-скриптинга. Начинайте с простых скриптов и постепенно усложняйте их по мере освоения материала!
