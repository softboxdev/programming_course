
## 1. Работа с файлами

### `fileinfo.sh` - Информация о файле
```bash
#!/bin/bash
# Показывает информацию о файле

# Запрашиваем имя файла
read -p "Введите путь к файлу: " filename

# Проверяем существует ли файл
if [ -e "$filename" ]; then
    echo "=== Информация о файле ==="
    echo "Имя: $(basename "$filename")"
    echo "Путь: $(dirname "$filename")"

    # Тип файла
    if [ -d "$filename" ]; then
        echo "Тип: Директория"
    elif [ -f "$filename" ]; then
        echo "Тип: Обычный файл"
    else
        echo "Тип: Другой"
    fi

    # Права доступа
    echo "Права: $(ls -l "$filename" | cut -d' ' -f1)"

    # Размер
    echo "Размер: $(du -h "$filename" | cut -f1)"
else
    echo "Файл не найден!"
fi
```

### `filecreate.sh` - Создание файлов
```bash
#!/bin/bash
# Создаёт файлы с разным содержимым

echo "Что создать?"
echo "1) Пустой файл"
echo "2) Файл с текстом"
echo "3) Файл с датой"
read -p "Выберите (1-3): " choice

case $choice in
    1)
        read -p "Имя файла: " filename
        touch "$filename"  # touch создаёт пустой файл
        echo "Создан пустой файл: $filename"
        ;;
    2)
        read -p "Имя файла: " filename
        read -p "Текст для записи: " text
        echo "$text" > "$filename"  # > перезаписывает файл
        echo "Файл создан с текстом"
        ;;
    3)
        read -p "Имя файла: " filename
        date > "$filename"  # Записываем текущую дату
        echo "Файл создан с текущей датой"
        cat "$filename"  # Показываем содержимое
        ;;
    *)
        echo "Неверный выбор"
        ;;
esac
```

### `copybackup.sh` - Копирование с резервной копией
```bash
#!/bin/bash
# Копирует файл с созданием бэкапа

read -p "Файл для копирования: " source
read -p "Куда копировать: " dest

# Проверяем исходный файл
if [ ! -f "$source" ]; then
    echo "Ошибка: Файл $source не найден!"
    exit 1
fi

# Если файл назначения существует, создаём бэкап
if [ -f "$dest" ]; then
    backup="${dest}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$dest" "$backup"
    echo "Создан бэкап: $backup"
fi

# Копируем файл
cp "$source" "$dest"
echo "Файл скопирован в: $dest"
```

### `filefind.sh` - Поиск файлов
```bash
#!/bin/bash
# Ищет файлы по имени в текущей директории

read -p "Введите часть имени для поиска: " pattern

echo "Ищем файлы с '$pattern'..."
echo "------------------------"

# find . - ищет в текущей директории
# -name "*$pattern*" - имя содержит шаблон
# -type f - только файлы (не директории)
find . -type f -name "*$pattern*" 2>/dev/null | while read file; do
    # Убираем ./ в начале
    echo "  ${file#./}"
done

# Считаем количество
count=$(find . -type f -name "*$pattern*" 2>/dev/null | wc -l)
echo "------------------------"
echo "Найдено файлов: $count"
```

### `filepermissions.sh` - Изменение прав
```bash
#!/bin/bash
# Меняет права доступа к файлу

read -p "Файл: " filename

if [ ! -e "$filename" ]; then
    echo "Файл не найден!"
    exit 1
fi

# Показываем текущие права
echo "Текущие права: $(ls -l "$filename" | cut -d' ' -f1)"

echo "Выберите действие:"
echo "1) Сделать исполняемым"
echo "2) Сделать только для чтения"
echo "3) Вернуть обычные права (644)"
read -p "Выберите (1-3): " choice

case $choice in
    1)
        chmod +x "$filename"  # Добавляем право на выполнение
        echo "Файл теперь исполняемый"
        ;;
    2)
        chmod 444 "$filename"  # Только чтение для всех
        echo "Файл теперь только для чтения"
        ;;
    3)
        chmod 644 "$filename"  # Стандартные права
        echo "Права сброшены на стандартные (644)"
        ;;
    *)
        echo "Неверный выбор"
        ;;
esac

echo "Новые права: $(ls -l "$filename" | cut -d' ' -f1)"
```

## 2. Работа с сетью

### `myip.sh` - Мой IP адрес
```bash
#!/bin/bash
# Показывает IP адреса компьютера

echo "=== Внутренние IP адреса ==="
# ip addr покажет все интерфейсы
# grep inet находит строки с IP
ip addr | grep inet | grep -v inet6 | while read line; do
    # Извлекаем IP (убираем маску /число)
    ip=$(echo "$line" | awk '{print $2}' | cut -d'/' -f1)
    # Пропускаем localhost
    if [ "$ip" != "127.0.0.1" ]; then
        echo "  $ip"
    fi
done

echo
echo "=== Внешний IP (через интернет) ==="
# curl запрашивает внешний IP через сервис
curl -s ifconfig.me
echo
```

### `pingtest.sh` - Проверка соединения
```bash
#!/bin/bash
# Проверяет доступность хоста

read -p "Введите адрес (google.com или IP): " host

echo "Проверяем соединение с $host..."
echo "------------------------"

# ping -c 4 отправляет 4 пакета
# -W 2 таймаут 2 секунды
ping -c 4 -W 2 "$host" | while read line; do
    if echo "$line" | grep -q "bytes from"; then
        # Извлекаем время ответа
        time=$(echo "$line" | grep -o "time=[0-9.]*" | cut -d= -f2)
        echo "✓ Ответ: ${time}ms"
    elif echo "$line" | grep -q "packet loss"; then
        # Извлекаем процент потерь
        loss=$(echo "$line" | grep -o "[0-9]*%")
        echo "Потеря пакетов: $loss"
    elif echo "$line" | grep -q "unknown host"; then
        echo "✗ Хост не найден!"
        exit 1
    fi
done
```

### `portscan.sh` - Проверка открытых портов
```bash
#!/bin/bash
# Проверяет открытые порты на локальной машине

echo "=== Открытые TCP порты ==="
# ss -tln показывает слушающие TCP порты
# grep -v 127.0.0.1 исключает локальные
ss -tln | grep LISTEN | grep -v 127.0.0.1 | while read line; do
    # Извлекаем порт
    port=$(echo "$line" | awk '{print $4}' | rev | cut -d: -f1 | rev)
    # Пытаемся определить сервис
    service=$(getent services "$port" 2>/dev/null | cut -d' ' -f1)
    if [ -n "$service" ]; then
        echo "  Порт $port ($service)"
    else
        echo "  Порт $port"
    fi
done

echo
echo "=== Открытые UDP порты ==="
ss -uln | grep UNCONN | grep -v 127.0.0.1 | while read line; do
    port=$(echo "$line" | awk '{print $5}' | rev | cut -d: -f1 | rev)
    service=$(getent services "$port" 2>/dev/null | cut -d' ' -f1)
    if [ -n "$service" ]; then
        echo "  Порт $port ($service)"
    else
        echo "  Порт $port"
    fi
done
```

### `download.sh` - Простой загрузчик
```bash
#!/bin/bash
# Скачивает файл из интернета

read -p "URL для скачивания: " url
read -p "Имя для сохранения: " filename

echo "Скачиваем $url ..."

# wget -O сохраняет с указанным именем
# -q тихий режим (без лишнего вывода)
if wget -O "$filename" "$url" 2>/dev/null; then
    echo "✓ Файл сохранён как: $filename"
    echo "Размер: $(du -h "$filename" | cut -f1)"
else
    echo "✗ Ошибка скачивания!"
fi
```

### `netstat.sh` - Сетевые соединения
```bash
#!/bin/bash
# Показывает активные сетевые соединения

echo "=== Активные соединения ==="
# ss -tun показывает все TCP/UDP соединения
ss -tun | tail -n +2 | while read line; do
    # Извлекаем состояние и адреса
    state=$(echo "$line" | awk '{print $1}')
    src=$(echo "$line" | awk '{print $5}')
    dst=$(echo "$line" | awk '{print $6}')

    # Пропускаем слушающие порты
    if [ "$state" != "LISTEN" ] && [ "$state" != "UNCONN" ]; then
        # Убираем IPv6 префикс если есть
        src_clean=$(echo "$src" | sed 's/\[::ffff://g' | sed 's/\]//g')
        dst_clean=$(echo "$dst" | sed 's/\[::ffff://g' | sed 's/\]//g')
        echo "  $src_clean -> $dst_clean ($state)"
    fi
done

# Считаем количество
count=$(ss -tun | tail -n +2 | grep -v LISTEN | grep -v UNCONN | wc -l)
echo "------------------------"
echo "Всего активных соединений: $count"
```

### `dnslookup.sh` - DNS запросы
```bash
#!/bin/bash
# Узнаёт IP адрес домена

read -p "Введите домен (например: google.com): " domain

echo "=== DNS информация для $domain ==="

# Получаем IP адреса
echo "IP адреса:"
dig +short "$domain" | while read ip; do
    echo "  $ip"
done

# Показываем полную информацию
echo
echo "Подробная информация:"
# nslookup показывает все записи
nslookup "$domain" | grep -v "Server:" | grep -v "Address:" | grep -v "Non-authoritative" | grep -v "^$" | while read line; do
    echo "  $line"
done
```

### `speedtest.sh` - Тест скорости (упрощённый)
```bash
#!/bin/bash
# Приблизительный тест скорости сети

echo "=== Тест скорости сети ==="
echo "Измеряем задержку..."

# Проверяем ping до Google DNS
ping_time=$(ping -c 3 8.8.8.8 | grep "avg" | grep -o "[0-9.]*" | tail -1)

if [ -n "$ping_time" ]; then
    echo "Задержка (ping): ${ping_time}ms"
else
    echo "Не удалось измерить задержку"
fi

echo
echo "Измеряем скорость скачивания..."
# Скачиваем тестовый файл и замеряем время
start=$(date +%s%N)
curl -s -o /tmp/speedtest https://speedtest.tele2.net/1MB.zip
end=$(date +%s%N)
duration=$((($end - $start)/1000000000))

if [ $duration -gt 0 ]; then
    speed=$((8 / $duration))  # 8MB = 8 мегабайт
    echo "Скорость: примерно ${speed} MB/s"
fi

rm -f /tmp/speedtest
```

## 3. Простые полезные скрипты

### `counter.sh` - Счётчик
```bash
#!/bin/bash
# Простой счётчик от 1 до N

read -p "До скольки считать? " max

# Проверяем что введено число
if ! [[ "$max" =~ ^[0-9]+$ ]]; then
    echo "Введите число!"
    exit 1
fi

echo "Считаем от 1 до $max:"

for ((i=1; i<=$max; i++)); do
    # Выводим с задержкой 0.5 секунды
    echo -n "$i "
    sleep 0.5
done

echo
echo "Готово!"
```

### `watcher.sh` - Мониторинг файла
```bash
#!/bin/bash
# Следит за изменениями в файле

read -p "Файл для наблюдения: " filename

if [ ! -f "$filename" ]; then
    echo "Файл не найден!"
    exit 1
fi

echo "Слежу за $filename (нажмите Ctrl+C для выхода)"
echo "Последние 3 строки:"

# tail -f показывает новые строки в реальном времени
tail -f "$filename"
```

### `menu.sh` - Простое меню
```bash
#!/bin/bash
# Пример меню с выбором действий

while true; do
    clear
    echo "=== ГЛАВНОЕ МЕНЮ ==="
    echo "1) Показать дату"
    echo "2) Показать кто в системе"
    echo "3) Показать свободное место"
    echo "4) Выход"
    echo
    read -p "Выберите пункт: " choice

    case $choice in
        1)
            date
            read -p "Нажмите Enter..."
            ;;
        2)
            who
            read -p "Нажмите Enter..."
            ;;
        3)
            df -h
            read -p "Нажмите Enter..."
            ;;
        4)
            echo "До свидания!"
            exit 0
            ;;
        *)
            echo "Неверный выбор!"
            read -p "Нажмите Enter..."
            ;;
    esac
done
```

## Как использовать:

1. **Создайте все скрипты**:
```bash
for script in fileinfo.sh filecreate.sh copybackup.sh filefind.sh filepermissions.sh myip.sh pingtest.sh portscan.sh download.sh netstat.sh dnslookup.sh speedtest.sh counter.sh watcher.sh menu.sh; do
    touch "$script"
    chmod +x "$script"
done
```

2. **Запускайте любой скрипт**:
```bash
./fileinfo.sh        # Информация о файле
./myip.sh           # Мой IP
./pingtest.sh       # Проверка соединения
./menu.sh           # Меню с выбором
```

## Основные команды для запоминания:

| Команда | Что делает |
|---------|------------|
| `ls` | Показать файлы |
| `cd` | Сменить директорию |
| `pwd` | Показать текущую директорию |
| `mkdir` | Создать папку |
| `rm` | Удалить файл |
| `cp` | Копировать файл |
| `mv` | Переместить/переименовать |
| `cat` | Показать содержимое файла |
| `grep` | Поиск в тексте |
| `find` | Поиск файлов |
| `ping` | Проверка сети |
| `curl` | Запросы к интернету |
| `ss` | Сетевые соединения |
| `chmod` | Изменить права |
| `date` | Показать дату |

Эти скрипты можно модифицировать, добавлять новые функции и комбинировать между собой!
