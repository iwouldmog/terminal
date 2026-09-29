#!/bin/sh
# Общие функции для скриптов тестирования эмулятора.
# Подключение: . "$(dirname "$0")/common.sh"

cd "$(dirname "$0")/.." || exit 1

# Вывести заголовок теста.
title() {
    printf '\n========== %s ==========\n' "$*"
}

# Запустить эмулятор с параметрами $@ и вывести код завершения.
# Ввод для эмулятора передаётся через stdin функции.
emulate() {
    echo "\$ ./run.sh $*"
    ./run.sh "$@" 2>&1
    echo "[exit code: $?]"
}

# Собрать ZIP-архив VFS build/$1.zip из каталога vfs/$1.
build_vfs() {
    "${PYTHON:-python3}" src/mkvfs.py "vfs/$1" "build/$1.zip" >/dev/null
}
