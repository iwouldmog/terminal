# Эмулятор командной оболочки UNIX

Практическая работа № 1 по дисциплине «Конфигурационное управление»,
вариант № 17.

## 1. Общее описание

Консольное приложение (CLI), имитирующее работу в командной строке
UNIX-подобной ОС. Реализовано на Python 3 без сторонних зависимостей.

Текущее состояние — **этап 3 (VFS)**: эмулятор принимает параметры
командной строки, выполняет стартовый скрипт и работает с виртуальной
файловой системой (VFS), загруженной из ZIP-архива в память.
Команды `ls` и `cd` пока являются заглушками.

Структура репозитория:

```
.
├── Makefile            цели для запуска, тестов и сборки VFS
├── run.sh              скрипт запуска эмулятора
├── scripts/            скрипты ОС для тестирования эмулятора
├── startup/            стартовые скрипты эмулятора
├── vfs/                исходное содержимое тестовых VFS
│   ├── minimal/        минимальная VFS (только motd)
│   ├── multi/          несколько файлов в корне, в т.ч. двоичный
│   └── deep/           вложенность каталогов до 4 уровней
├── src/                исходный код
│   ├── main.py         точка входа
│   ├── config.py       параметры командной строки
│   ├── shell.py        оболочка: REPL и стартовые скрипты
│   ├── line_parser.py  разбор строки на команду и аргументы
│   ├── commands.py     встроенные команды
│   ├── vfs.py          виртуальная файловая система в памяти
│   ├── mkvfs.py        сборка ZIP-архива VFS из каталога
│   └── errors.py       исключения и коды завершения
└── tests/              модульные тесты (unittest)
```

ZIP-архивы в репозитории не хранятся: они собираются из каталогов
`vfs/*` командой `make vfs` в каталог `build/` (исключён из git).

## 2. Функции и настройки

### Параметры командной строки

```
./run.sh [-h] [--vfs PATH] [--script PATH]
```

| Параметр        | Описание                                           |
|-----------------|----------------------------------------------------|
| `--vfs PATH`    | путь к физическому расположению VFS (ZIP-архив)    |
| `--script PATH` | путь к стартовому скрипту                          |
| `-h`, `--help`  | справка по параметрам                              |

Значения можно задавать как `--vfs PATH`, так и `--vfs=PATH`.
При запуске выводится отладочная информация обо всех параметрах и о
загруженной VFS:

```
[debug] vfs: build/deep.zip
[debug] script: (not set)
[debug] vfs loaded: name=deep, directories=12, files=9
```

### Виртуальная файловая система

- Источник VFS — ZIP-архив. Он читается целиком в память и **не
  распаковывается**; все операции выполняются в памяти, архив не
  изменяется (кроме служебной команды `vfs-init`).
- Каталоги берутся как из явных элементов архива (`dir/`), так и из
  путей файлов (`a/b/c.txt` создаёт каталоги `a` и `a/b`).
- Двоичные данные хранятся в памяти как есть, а при выводе на экран
  кодируются в **base64**. В репозитории двоичные файлы тестовых VFS
  хранятся в текстовом виде `*.b64` и декодируются при сборке архива.
- Без `--vfs` используется VFS по умолчанию — пустой корневой
  каталог с именем `vfs`.
- Если в корне VFS есть файл `motd`, его текст выводится при старте.

Сборка архива из каталога:

```bash
python3 src/mkvfs.py vfs/deep build/deep.zip
```

### Приглашение к вводу

Приглашение содержит имя VFS (имя архива без расширения) и текущий
каталог: `deep:/$ `.

### Стартовый скрипт

Текстовый файл (UTF-8) с командами эмулятора, по одной на строку.

- Команды выполняются последовательно; каждая строка выводится после
  приглашения, затем выводится результат — как в диалоге.
- Пустые строки пропускаются, `#` начинает комментарий.
- Строки с ошибками выводят сообщение и пропускаются.
- `exit` завершает эмулятор; если скрипт закончился без `exit`,
  продолжается диалог с пользователем.
- Если скрипт не удалось прочитать, эмулятор завершается с кодом 1.

Примеры скриптов лежат в каталоге `startup/`.

### Команды

| Команда    | Описание                                                |
|------------|---------------------------------------------------------|
| `ls ...`   | заглушка: выводит `ls: args=[...]`                      |
| `cd ...`   | заглушка: выводит `cd: args=[...]`                      |
| `exit [N]` | завершает эмулятор с кодом `N` (по модулю 256); без     |
|            | аргумента — с кодом последней команды, как в bash       |
| `vfs-init` | заменяет текущую VFS на VFS по умолчанию (пустую) и     |
|            | перезаписывает её ZIP-архив пустым архивом              |

### Обработка ошибок

| Ситуация                        | Сообщение                                  | Код |
|---------------------------------|--------------------------------------------|-----|
| неверные параметры запуска      | сообщение `argparse` и справка             | 2   |
| скрипт не найден / не читается  | `emulator: cannot read script '...'`       | 1   |
| архив VFS не найден / каталог   | `emulator: cannot load VFS '...': ...`     | 1   |
| файл VFS не является ZIP        | `...: File is not a zip file`              | 1   |
| конфликт имён или `..` в архиве | `...: invalid archive` / `unsafe path`     | 1   |
| неизвестная команда             | `foo: command not found`                   | 127 |
| нечисловой аргумент `exit`      | `exit: abc: numeric argument required`     | 1   |
| лишние аргументы                | `exit: too many arguments`                 | 1   |
| архив недоступен для записи     | `vfs-init: cannot write '...': ...`        | 1   |
| Ctrl+C во время ввода           | ввод строки прерывается, работа идёт       | 130 |
| Ctrl+D (конец ввода)            | эмулятор завершается                       | —   |

Ошибки выводятся в stderr, после ошибки команды диалог продолжается.

### Основные функции (модули `src/`)

| Функция / класс                   | Назначение                            |
|-----------------------------------|---------------------------------------|
| `config.parse_args`               | разобрать параметры командной строки  |
| `config.print_config`             | отладочный вывод параметров           |
| `line_parser.parse_line`          | разбить строку на команду и аргументы |
| `shell.Shell.prompt`              | приглашение: имя VFS и каталог        |
| `shell.Shell.execute`             | выполнить строку, вернуть код         |
| `shell.Shell.repl`                | цикл чтения и выполнения команд       |
| `shell.Shell.run_script`          | выполнить стартовый скрипт            |
| `shell.Shell.run`                 | скрипт, затем диалог; вернуть код     |
| `shell.Shell.show_motd`           | вывести `motd` из корня VFS           |
| `vfs.VirtualFileSystem.from_zip`  | загрузить VFS из архива в память      |
| `vfs.VirtualFileSystem.empty`     | создать VFS по умолчанию              |
| `vfs.VirtualFileSystem.reset`     | очистить VFS и её архив               |
| `vfs.VirtualFileSystem.count`     | число каталогов и файлов              |
| `vfs.decode_content`              | текст файла; двоичные данные — base64 |
| `mkvfs.build_archive`             | собрать ZIP-архив из каталога         |
| `commands.cmd_*`                  | реализации встроенных команд          |

## 3. Сборка и запуск тестов

Нужен Python 3.9 или новее, сторонние пакеты не требуются.

```bash
make vfs          # собрать архивы build/{minimal,multi,deep}.zip
./run.sh --vfs build/deep.zip --script startup/stage3.txt
make run ARGS="--vfs build/deep.zip"   # запуск через make
make test         # модульные тесты
make demo         # все скрипты ОС из scripts/
make clean        # удалить build/ и служебные файлы
```

Тесты без `make`:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Скрипты ОС для тестирования (каждый сам собирает нужные архивы):

| Скрипт                           | Что проверяет                           |
|----------------------------------|-----------------------------------------|
| `scripts/test_params.sh`         | все сочетания параметров, `--help`      |
| `scripts/test_params_errors.sh`  | ошибки в параметрах и в скрипте         |
| `scripts/test_startup_script.sh` | выполнение скриптов с разными VFS       |
| `scripts/test_vfs_minimal.sh`    | VFS по умолчанию и минимальная VFS      |
| `scripts/test_vfs_multi.sh`      | VFS из нескольких файлов                |
| `scripts/test_vfs_deep.sh`       | VFS с вложенностью не менее 3 уровней   |
| `scripts/test_vfs_errors.sh`     | ошибки загрузки VFS и `vfs-init`        |

Стартовый скрипт `startup/stage3.txt` проверяет все команды этапов
1–3, включая обработку ошибок и `vfs-init`.

## 4. Примеры использования

Стартовый скрипт этапа 3 на VFS из нескольких файлов:

```
$ ./run.sh --vfs build/multi.zip --script startup/stage3.txt
[debug] vfs: build/multi.zip
[debug] script: startup/stage3.txt
[debug] vfs loaded: name=multi, directories=0, files=7
Welcome to the "multi" VFS.
It contains several files in the root directory.
multi:/$ # Стартовый скрипт этапа 3: все команды этапов 1-3 и работа с VFS.
multi:/$ # Внимание: vfs-init очищает физический ZIP-архив VFS.
multi:/$ # Команды-заглушки ls и cd
multi:/$ ls
ls: args=[]
multi:/$ ls -l /home/user
ls: args=['-l', '/home/user']
multi:/$ cd /etc
cd: args=['/etc']
multi:/$ # Ошибки: выполнение скрипта продолжается
multi:/$ no-such-command
no-such-command: command not found
multi:/$ exit abc
exit: abc: numeric argument required
multi:/$ exit 1 2
exit: too many arguments
multi:/$ vfs-init extra-argument
vfs-init: too many arguments
multi:/$ # Замена VFS на VFS по умолчанию (пустую)
multi:/$ vfs-init
multi:/$ ls
ls: args=[]
multi:/$ exit 0
```

После `vfs-init` архив пуст:

```
$ ./run.sh --vfs build/multi.zip
[debug] vfs: build/multi.zip
[debug] script: (not set)
[debug] vfs loaded: name=multi, directories=0, files=0
multi:/$
```

Ошибки загрузки VFS:

```
$ ./run.sh --vfs build/missing.zip
[debug] vfs: build/missing.zip
[debug] script: (not set)
emulator: cannot load VFS 'build/missing.zip': No such file or directory
$ ./run.sh --vfs README.md
[debug] vfs: README.md
[debug] script: (not set)
emulator: cannot load VFS 'README.md': File is not a zip file
```
