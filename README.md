# Эмулятор командной оболочки UNIX

Практическая работа № 1 по дисциплине «Конфигурационное управление»,
вариант № 17.

## 1. Общее описание

Консольное приложение (CLI), имитирующее работу в командной строке
UNIX-подобной ОС. Реализовано на Python 3 без сторонних зависимостей.

Эмулятор:

- ведёт диалог с пользователем (REPL) с приглашением вида
  `deep:/home/user$ `, где `deep` — имя VFS;
- принимает параметры командной строки и выполняет стартовый скрипт;
- работает с виртуальной файловой системой (VFS), загруженной из
  ZIP-архива целиком в память;
- поддерживает команды `ls`, `cd`, `pwd`, `cat`, `tac`, `rm`, `touch`,
  `exit` и служебную команду `vfs-init`.

Все пять этапов работы выполнены. Каждому этапу соответствует коммит
и тег `stage-1` … `stage-5`:

| Этап | Тег       | Содержание                                          |
|------|-----------|-----------------------------------------------------|
| 1    | `stage-1` | REPL, парсер, заглушки `ls`/`cd`, команда `exit`    |
| 2    | `stage-2` | параметры `--vfs`/`--script`, стартовый скрипт      |
| 3    | `stage-3` | VFS из ZIP в памяти, `motd`, `vfs-init`             |
| 4    | `stage-4` | команды `ls`, `cd`, `pwd`, `cat`, `tac`             |
| 5    | `stage-5` | команды `rm`, `touch` (изменения только в памяти)   |

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
  распаковывается**. Все операции, включая `rm` и `touch`,
  выполняются только в памяти; архив не изменяется. Исключение —
  служебная команда `vfs-init`.
- Каталоги берутся как из явных элементов архива (`dir/`), так и из
  путей файлов (`a/b/c.txt` создаёт каталоги `a` и `a/b`).
- Двоичные данные хранятся в памяти как есть, а при выводе на экран
  кодируются в **base64**. В репозитории двоичные файлы тестовых VFS
  хранятся в текстовом виде `*.b64` и декодируются при сборке архива.
- Без `--vfs` используется VFS по умолчанию — пустой корневой
  каталог с именем `vfs`.
- Если в корне VFS есть файл `motd`, его текст выводится при старте.

Сборка архива из каталога (`*.b64` → двоичные файлы):

```bash
python3 src/mkvfs.py vfs/deep build/deep.zip
```

### Приглашение к вводу

Приглашение содержит имя VFS (имя архива без расширения) и текущий
каталог: `deep:/home/user$ `.

### Стартовый скрипт

Текстовый файл (UTF-8) с командами эмулятора, по одной на строку.

- Команды выполняются последовательно; каждая строка выводится после
  приглашения, затем выводится результат — как в диалоге.
- Пустые строки пропускаются, `#` начинает комментарий.
- Строки с ошибками выводят сообщение и пропускаются.
- `exit` завершает эмулятор; если скрипт закончился без `exit`,
  продолжается диалог с пользователем.
- Если скрипт не удалось прочитать, эмулятор завершается с кодом 1.

### Разбор команд

Строка разделяется на команду и аргументы по пробельным символам.
Слово, начинающееся с `#`, открывает комментарий до конца строки.
Если ввод идёт не с терминала (например, через канал), введённая
строка повторяется после приглашения, чтобы вывод выглядел как диалог.

### Команды

| Команда                  | Описание                                    |
|--------------------------|---------------------------------------------|
| `ls [-a] [-l] [PATH...]` | содержимое каталогов (для файла — его имя)  |
| `cd [DIR]`               | сменить каталог; без аргумента — в корень   |
| `pwd`                    | вывести абсолютный путь текущего каталога   |
| `cat [-n] FILE...`       | вывести содержимое файлов                   |
| `tac FILE...`            | вывести строки файлов в обратном порядке    |
| `rm [-r] [-f] PATH...`   | удалить файлы и каталоги (в памяти)         |
| `touch [-c] FILE...`     | создать пустые файлы / обновить время       |
| `exit [N]`               | завершить эмулятор с кодом `N`              |
| `vfs-init`               | заменить VFS на VFS по умолчанию            |

Подробности:

- **Пути** — абсолютные (`/etc/hostname`) и относительные
  (`../docs/./a.txt`); `..` в корне указывает на корень; путь через
  файл (`hostname/..`) — ошибка `Not a directory`.
- **Опции** — короткие, объединяются (`-la`, `-rf`), могут стоять
  после операндов; `--` завершает список опций.
- **`ls`**: имена выводятся в одну строку по алфавиту через два
  пробела. `-a` показывает скрытые файлы (имя начинается с `.`), а
  также `.` и `..`. `-l` — подробный формат:
  `drwxr-xr-x   4096 2026-09-29 15:01 docs` (тип и права, размер,
  время изменения, имя). При нескольких операндах сначала выводятся
  файлы, затем каталоги с заголовками `путь:`, как в GNU ls.
- **`cat -n`** нумерует строки сквозной нумерацией по всем файлам.
- **`cat`/`tac`** выводят двоичные файлы в base64; ошибка в одном
  файле не мешает выводу остальных (код завершения 1).
- **`rm`**: каталоги удаляются только с `-r` (или `-R`); `-f` не
  сообщает об отсутствующих путях (другие ошибки сообщаются).
  Удалить корень, `.` и `..` нельзя. Если удалён текущий каталог (или
  содержащий его), выполняется переход в родителя удалённого.
- **`touch`** создаёт пустой файл, если его нет, иначе обновляет время
  изменения (и у каталогов); `-c` — не создавать файлы.
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
| нет операндов                   | `cat: missing file operand`                | 1   |
| неизвестная опция               | `ls: invalid option -- 'x'`                | 1   |
| длинная опция                   | `ls: unrecognized option '--all'`          | 1   |
| `rm` каталога без `-r`          | `rm: cannot remove 'x': Is a directory`    | 1   |
| `rm -r /`                       | `rm: it is dangerous to operate ...`       | 1   |
| `rm .` или `rm ..`              | `rm: refusing to remove '.' or '..' ...`   | 1   |
| `touch` в отсутствующий каталог | `touch: cannot touch 'x': No such file...` | 1   |
| архив недоступен для записи     | `vfs-init: cannot write '...': ...`        | 1   |
| Ctrl+C во время ввода           | ввод строки прерывается, работа идёт       | 130 |
| Ctrl+D (конец ввода)            | эмулятор завершается                       | —   |

Ошибки выводятся в stderr, после ошибки команды диалог продолжается.

### Основные функции (модули `src/`)

| Функция / класс                     | Назначение                            |
|-------------------------------------|---------------------------------------|
| `config.parse_args`                 | разобрать параметры командной строки  |
| `config.print_config`               | отладочный вывод параметров           |
| `line_parser.parse_line`            | разбить строку на команду и аргументы |
| `shell.Shell.prompt`                | приглашение: имя VFS и каталог        |
| `shell.Shell.execute`               | выполнить строку, вернуть код         |
| `shell.Shell.repl`                  | цикл чтения и выполнения команд       |
| `shell.Shell.run_script`            | выполнить стартовый скрипт            |
| `shell.Shell.run`                   | скрипт, затем диалог; вернуть код     |
| `shell.Shell.show_motd`             | вывести `motd` из корня VFS           |
| `vfs.VirtualFileSystem.from_zip`    | загрузить VFS из архива в память      |
| `vfs.VirtualFileSystem.empty`       | создать VFS по умолчанию              |
| `vfs.VirtualFileSystem.reset`       | очистить VFS и её архив               |
| `vfs.VirtualFileSystem.resolve`     | найти узел по пути (с `.` и `..`)     |
| `vfs.VirtualFileSystem.create_file` | создать пустой файл в памяти          |
| `vfs.VirtualFileSystem.remove`      | удалить узел в памяти                 |
| `vfs.VirtualFileSystem.count`       | число каталогов и файлов              |
| `vfs.decode_content`                | текст файла; двоичные данные — base64 |
| `mkvfs.build_archive`               | собрать ZIP-архив из каталога         |
| `commands.split_options`            | отделить опции от операндов           |
| `commands.cmd_ls`                   | команда `ls`                          |
| `commands.cmd_cd`, `cmd_pwd`        | команды `cd` и `pwd`                  |
| `commands.cmd_cat`, `cmd_tac`       | команды `cat` и `tac`                 |
| `commands.cmd_rm`, `cmd_touch`      | команды `rm` и `touch`                |
| `commands.cmd_exit`                 | команда `exit`                        |
| `commands.cmd_vfs_init`             | команда `vfs-init`                    |

## 3. Сборка и запуск тестов

Нужен Python 3.9 или новее, сторонние пакеты не требуются.

```bash
make vfs          # собрать архивы build/{minimal,multi,deep}.zip
./run.sh --vfs build/deep.zip --script startup/stage5.txt
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

| Скрипт                           | Этап | Что проверяет                       |
|----------------------------------|------|-------------------------------------|
| `scripts/test_params.sh`         | 2    | все сочетания параметров, `--help`  |
| `scripts/test_params_errors.sh`  | 2    | ошибки в параметрах и в скрипте     |
| `scripts/test_startup_script.sh` | 2    | выполнение скриптов с разными VFS   |
| `scripts/test_vfs_minimal.sh`    | 3    | VFS по умолчанию и минимальная VFS  |
| `scripts/test_vfs_multi.sh`      | 3    | VFS из нескольких файлов            |
| `scripts/test_vfs_deep.sh`       | 3    | VFS с вложенностью от 3 уровней     |
| `scripts/test_vfs_errors.sh`     | 3    | ошибки загрузки VFS и `vfs-init`    |
| `scripts/test_commands.sh`       | 4    | `ls`, `cd`, `pwd`, `cat`, `tac`     |
| `scripts/test_modify.sh`         | 5    | `rm`, `touch`; архив не изменяется  |

Стартовые скрипты эмулятора:

| Скрипт                    | Что проверяет                                |
|---------------------------|----------------------------------------------|
| `startup/stage2.txt`      | выполнение скрипта, пропуск ошибочных строк  |
| `startup/stage2_exit.txt` | досрочный `exit` из скрипта                  |
| `startup/stage3.txt`      | все команды этапов 1–3 и `vfs-init`          |
| `startup/stage4.txt`      | все режимы `ls`, `cd`, `pwd`, `cat`, `tac`   |
| `startup/stage5.txt`      | все режимы `rm` и `touch`                    |

Скрипты `stage4.txt` и `stage5.txt` рассчитаны на VFS `build/deep.zip`.

## 4. Примеры использования

Интерактивный сеанс:

```
$ make vfs
$ ./run.sh --vfs build/deep.zip
[debug] vfs: build/deep.zip
[debug] script: (not set)
[debug] vfs loaded: name=deep, directories=12, files=9
Welcome to the "deep" VFS!
Directories are nested up to 4 levels: /home/user/docs/drafts
deep:/$ ls
bin  etc  home  motd  var
deep:/$ cd home/user/docs
deep:/home/user/docs$ touch notes.txt
deep:/home/user/docs$ ls -l
drwxr-xr-x   4096 2026-09-29 15:01 drafts
-rw-r--r--      0 2026-09-29 15:10 notes.txt
-rw-r--r--     71 2026-09-29 15:01 report.txt
deep:/home/user/docs$ rm -r drafts
deep:/home/user/docs$ ls
notes.txt  report.txt
deep:/home/user/docs$ cd /
deep:/$ rm home
rm: cannot remove 'home': Is a directory
deep:/$ exit 0
```

Навигация и просмотр файлов (фрагмент `startup/stage4.txt`):

```
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
deep:/$ cat missing.txt /etc/hostname
cat: missing.txt: No such file or directory
emulator
```

Изменение VFS (фрагмент `startup/stage5.txt`):

```
deep:/$ cd /home/user
deep:/home/user$ touch new.txt /tmp.txt docs/drafts/idea.txt
deep:/home/user$ ls
docs  new.txt  projects
deep:/home/user$ touch -c ghost.txt
deep:/home/user$ rm -r docs/drafts
deep:/home/user$ ls docs
report.txt
deep:/home/user$ cd /var/log/app
deep:/var/log/app$ rm -R /var/log
deep:/var$ pwd
/var
deep:/var$ touch /etc/hostname/file.txt
touch: cannot touch '/etc/hostname/file.txt': Not a directory
deep:/var$ rm /home
rm: cannot remove '/home': Is a directory
deep:/var$ rm -r /
rm: it is dangerous to operate recursively on '/'
deep:/var$ rm -r ..
rm: refusing to remove '.' or '..' directory: skipping '..'
```

Служебная команда `vfs-init` (архив очищается):

```
$ ./run.sh --vfs build/multi.zip
[debug] vfs: build/multi.zip
[debug] script: (not set)
[debug] vfs loaded: name=multi, directories=0, files=7
Welcome to the "multi" VFS.
It contains several files in the root directory.
multi:/$ vfs-init
multi:/$ ls
multi:/$ exit
$ ./run.sh --vfs build/multi.zip
[debug] vfs: build/multi.zip
[debug] script: (not set)
[debug] vfs loaded: name=multi, directories=0, files=0
multi:/$
```

Ошибки запуска:

```
$ ./run.sh --vfs
usage: emulator [-h] [--vfs PATH] [--script PATH]
emulator: error: argument --vfs: expected one argument
$ ./run.sh --vfs build/missing.zip
[debug] vfs: build/missing.zip
[debug] script: (not set)
emulator: cannot load VFS 'build/missing.zip': No such file or directory
$ ./run.sh --vfs README.md
[debug] vfs: README.md
[debug] script: (not set)
emulator: cannot load VFS 'README.md': File is not a zip file
$ ./run.sh --script startup/missing.txt
[debug] vfs: (not set)
[debug] script: startup/missing.txt
[debug] vfs loaded: name=vfs, directories=0, files=0
emulator: cannot read script 'startup/missing.txt': No such file or directory
```
