# Эмулятор командной оболочки UNIX

Практическая работа № 1 по дисциплине «Конфигурационное управление»,
вариант № 17.

## 1. Общее описание

Консольное приложение (CLI), имитирующее работу в командной строке
UNIX-подобной ОС. Реализовано на Python 3 без сторонних зависимостей.

Текущее состояние — **этап 4 (основные команды)**: эмулятор принимает
параметры командной строки, выполняет стартовый скрипт и работает с
виртуальной файловой системой (VFS), загруженной из ZIP-архива в
память. Поддерживаются команды `ls`, `cd`, `pwd`, `cat`, `tac`,
`exit` и служебная `vfs-init`.

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

| Команда                  | Описание                                    |
|--------------------------|---------------------------------------------|
| `ls [-a] [-l] [PATH...]` | содержимое каталогов (для файла — его имя)  |
| `cd [DIR]`               | сменить каталог; без аргумента — в корень   |
| `pwd`                    | вывести абсолютный путь текущего каталога   |
| `cat [-n] FILE...`       | вывести содержимое файлов                   |
| `tac FILE...`            | вывести строки файлов в обратном порядке    |
| `exit [N]`               | завершить эмулятор с кодом `N`              |
| `vfs-init`               | заменить VFS на VFS по умолчанию            |

Подробности:

- **Пути** — абсолютные (`/etc/hostname`) и относительные
  (`../docs/./a.txt`); `..` в корне указывает на корень; путь через
  файл (`hostname/..`) — ошибка `Not a directory`.
- **Опции** — короткие, объединяются (`-la`), могут стоять после
  операндов; `--` завершает список опций.
- **`ls`**: имена выводятся в одну строку по алфавиту через два
  пробела. `-a` показывает скрытые файлы (имя начинается с `.`), а
  также `.` и `..`. `-l` — подробный формат:
  `drwxr-xr-x   4096 2026-09-29 15:01 docs` (тип и права, размер,
  время изменения, имя). При нескольких операндах сначала выводятся
  файлы, затем каталоги с заголовками `путь:`, как в GNU ls.
- **`cat -n`** нумерует строки сквозной нумерацией по всем файлам.
- **`cat`/`tac`** выводят двоичные файлы в base64; ошибка в одном
  файле не мешает выводу остальных (код завершения 1).
- **`exit [N]`**: код по модулю 256; без аргумента — код последней
  команды, как в bash.
- **`vfs-init`** заменяет текущую VFS на VFS по умолчанию (пустую),
  перезаписывает её ZIP-архив пустым архивом и переходит в корень.

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
| лишние аргументы                | `cd: too many arguments`                   | 1   |
| путь не существует              | `cd: x: No such file or directory`         | 1   |
| `ls` для несуществующего пути   | `ls: cannot access 'x': No such file ...`  | 2   |
| `cd` в файл                     | `cd: x: Not a directory`                   | 1   |
| `cat`/`tac` для каталога        | `cat: x: Is a directory`                   | 1   |
| `cat`/`tac` без операндов       | `cat: missing file operand`                | 1   |
| неизвестная опция               | `ls: invalid option -- 'x'`                | 1   |
| длинная опция                   | `ls: unrecognized option '--all'`          | 1   |
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
| `vfs.VirtualFileSystem.resolve`   | найти узел по пути (с `.` и `..`)     |
| `commands.split_options`          | отделить опции от операндов           |
| `commands.cmd_ls`                 | команда `ls`                          |
| `commands.cmd_cd`, `cmd_pwd`      | команды `cd` и `pwd`                  |
| `commands.cmd_cat`, `cmd_tac`     | команды `cat` и `tac`                 |
| `commands.cmd_exit`               | команда `exit`                        |
| `commands.cmd_vfs_init`           | команда `vfs-init`                    |

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
| `scripts/test_commands.sh`       | `ls`, `cd`, `pwd`, `cat`, `tac`         |

Стартовые скрипты эмулятора:

| Скрипт                    | Что проверяет                                |
|---------------------------|----------------------------------------------|
| `startup/stage2.txt`      | выполнение скрипта, пропуск ошибочных строк  |
| `startup/stage2_exit.txt` | досрочный `exit` из скрипта                  |
| `startup/stage3.txt`      | все команды этапов 1–3 и `vfs-init`          |
| `startup/stage4.txt`      | все режимы `ls`, `cd`, `pwd`, `cat`, `tac`   |

## 4. Примеры использования

Основные команды на глубокой VFS (фрагмент `startup/stage4.txt`):

```
$ ./run.sh --vfs build/deep.zip
[debug] vfs: build/deep.zip
[debug] script: (not set)
[debug] vfs loaded: name=deep, directories=12, files=9
Welcome to the "deep" VFS!
Directories are nested up to 4 levels: /home/user/docs/drafts
deep:/$ ls
bin  etc  home  motd  var
deep:/$ cd home/user/docs/drafts
deep:/home/user/docs/drafts$ cd ../../projects/./emulator
deep:/home/user/projects/emulator$ pwd
/home/user/projects/emulator
deep:/home/user/projects/emulator$ cd
deep:/$ ls -a /home/user
.  ..  .bashrc  docs  projects
deep:/$ ls -la home/user/docs
drwxr-xr-x   4096 2026-09-29 15:01 .
drwxr-xr-x   4096 2026-09-29 15:01 ..
drwxr-xr-x   4096 2026-09-29 15:01 drafts
-rw-r--r--     71 2026-09-29 15:01 report.txt
deep:/$ ls /var/log /etc
/etc:
hostname  network

/var/log:
app
deep:/$ cat -n home/user/docs/drafts/plan.txt
     1	step 1: design
     2	step 2: implement
     3	step 3: test
     4	step 4: release
deep:/$ tac var/log/app/app.log
2026-09-01 10:02:00 INFO stopped
2026-09-01 10:01:00 ERROR connection lost
2026-09-01 10:00:05 WARN low memory
2026-09-01 10:00:00 INFO started
deep:/$ cat bin/hello
f0VMRgIBAQAAAwYJDA8SFRgbHiEkJyotMDM2OTw/QkVIS05RVFdaXWBjZmlsb3J1eHt+gYSHio2Q
k5aZnJ+ipairrrG0t7q9wMPGyczP0tXY297h5Ofq7fDz9vn8/w==
deep:/$ cd /etc/hostname
cd: /etc/hostname: Not a directory
deep:/$ ls /nonexistent
ls: cannot access '/nonexistent': No such file or directory
deep:/$ cat missing.txt /etc/hostname
cat: missing.txt: No such file or directory
emulator
deep:/$ ls --all
ls: unrecognized option '--all'
deep:/$ exit 0
```

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
multi:/$ # Команды ls и cd
multi:/$ ls
data.csv  empty.txt  logo.png  motd  notes.txt  readme.txt
multi:/$ ls -l /
-rw-r--r--     45 2026-09-29 15:01 data.csv
-rw-r--r--      0 2026-09-29 15:01 empty.txt
-rw-r--r--     70 2026-09-29 15:03 logo.png
-rw-r--r--     77 2026-09-29 15:01 motd
-rw-r--r--     72 2026-09-29 15:01 notes.txt
-rw-r--r--     84 2026-09-29 15:01 readme.txt
multi:/$ cd /
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
