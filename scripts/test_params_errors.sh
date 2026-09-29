#!/bin/sh
# Этап 2: ошибки в параметрах командной строки.
. "$(dirname "$0")/common.sh"

title "Неизвестный параметр"
emulate --vfs demo.zip --script startup/stage2.txt --verbose </dev/null

title "Параметр --vfs без значения"
emulate --script startup/stage2.txt --vfs </dev/null

title "Параметр --script без значения"
emulate --vfs demo.zip --script </dev/null

title "Лишний позиционный аргумент"
emulate --vfs demo.zip --script startup/stage2.txt extra </dev/null

title "Стартовый скрипт не существует"
emulate --vfs demo.zip --script startup/missing.txt </dev/null

title "Стартовый скрипт является каталогом"
emulate --vfs demo.zip --script startup </dev/null
