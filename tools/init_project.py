#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
init_project.py
---------------
Создаёт проект, структуру папок, локальный и удалённый git-репозиторий на GitHub,
разворачивает venv и делает первый коммит (включая указанный файл данных/скрипт).

Пример:
  python init_project.py --name meeting-automation \
    --description "Автоматизация заметок и обработки встреч" \
    --data-file meeting_automation.py
"""

import os
import sys
import subprocess
import shutil
import argparse
from pathlib import Path

# ---------------------------
# Bootstrap ensure `requests`
# ---------------------------

def in_venv() -> bool:
    return (
        hasattr(sys, "real_prefix") or
        (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix) or
        ("VIRTUAL_ENV" in os.environ)
    )

def ensure_requests():
    try:
        import requests  # noqa: F401
        return
    except Exception:
        pass

    if in_venv():
        # Уже в активном venv — просим явно установить
        print(
            "✖ Модуль 'requests' не найден в активном виртуальном окружении.\n"
            "  Установите и повторите запуск:\n"
            "    pip install requests\n",
            file=sys.stderr,
        )
        sys.exit(1)

    # Не в venv: бутстрапим временное окружение и перезапускаем скрипт из него
    if os.environ.get("BOOTSTRAPPED_REQUESTS") == "1":
        print(
            "✖ Не удалось загрузить 'requests' после бутстрапа.\n"
            "  Установите вручную или проверьте доступ к сети.",
            file=sys.stderr,
        )
        sys.exit(1)

    venv_dir = Path(".venv-init")
    py = sys.executable

    print("⚙️  Создаю временное окружение .venv-init для установки 'requests'...")
    if venv_dir.exists():
        shutil.rmtree(venv_dir)
    subprocess.check_call([py, "-m", "venv", str(venv_dir)])

    bin_dir = "Scripts" if os.name == "nt" else "bin"
    pip_path = venv_dir / bin_dir / ("pip.exe" if os.name == "nt" else "pip")
    py_path = venv_dir / bin_dir / ("python.exe" if os.name == "nt" else "python")

    subprocess.check_call([str(pip_path), "install", "--upgrade", "pip"])
    subprocess.check_call([str(pip_path), "install", "requests"])

    print("🔁 Перезапускаю скрипт с .venv-init ...")
    env = os.environ.copy()
    env["BOOTSTRAPPED_REQUESTS"] = "1"
    os.execve(str(py_path), [str(py_path), *sys.argv], env)

ensure_requests()
import requests  # noqa: E402

# ---------------------------
# CLI
# ---------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Инициализация проекта и GitHub репозитория")
    p.add_argument("--name", required=True, help="Имя проекта / репозитория")
    p.add_argument("--description", default="", help="Описание проекта")
    p.add_argument("--private", action="store_true", help="Создать приватный репозиторий на GitHub")
    p.add_argument("--data-file", default=None, help="Путь к файлу (скрипт/данные) для первого коммита")
    p.add_argument("--no-remote", action="store_true", help="Не создавать удалённый репозиторий (офлайн режим)")
    return p.parse_args()

# ---------------------------
# Утилиты
# ---------------------------

def run(cmd, cwd=None, check=True):
    print(f"▶ {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), check=check)

def git(*args, cwd=None):
    run(["git", *args], cwd=cwd)

def write_text(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

# ---------------------------
# Контент файлов
# ---------------------------

GITIGNORE = """\
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
*.sqlite3

# Envs
venv/
.env
.venv
.venv-init/

# Editors
.vscode/
.idea/

# OS
.DS_Store

# Data
data/raw/*
!data/.gitkeep
"""


README_TMPL = """# {name}
{description}
## Быстрый старт
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate.bat
pip install -r requirements.txt
```
"""

REQUIREMENTS = """
requests
"""

 #—————————
# Основная логика

# —————————

def create_structure(project: Path, name: str, description: str, data_file: str | None):

    (project / "src").mkdir(parents=True, exist_ok=True)
    (project / "data" / "raw").mkdir(parents=True, exist_ok=True)
    (project / "data" / ".gitkeep").write_text("", encoding="utf-8")

    write_text(project / ".gitignore", GITIGNORE)
    write_text(project / "README.md", README_TMPL.format(name=name, description=description))
    write_text(project / "requirements.txt", REQUIREMENTS)

    if data_file:
        src = Path(data_file).expanduser().resolve()
        if not src.exists():
            print(f"⚠️  Файл для первого коммита не найден: {src}", file=sys.stderr)
        else:
            dst = project / src.name
            shutil.copy2(src, dst)
            print(f"📦 Скопирован файл {src} → {dst}")
def create_project_venv(project: Path):
    print("⚙️  Создаю проектное виртуальное окружение venv …")
    run([sys.executable, "-m", "venv", str(project / "venv")])
    print(
        "💡 Активируйте окружение:\n"
        + r"  source venv/bin/activate  # Windows: venv\Scripts\activate.bat"
    )

def init_git_and_first_commit(project: Path):
    git("init", cwd=project)
    git("add", ".", cwd=project)
    git("commit", "-m", "chore: init project skeleton", cwd=project)
    try:
        git("branch", "-M", "main", cwd=project)
    except Exception:
        pass

def create_github_repo_and_push(project: Path, name: str, description: str, private: bool):
    username = os.environ.get("GITHUB_USERNAME")
    token = os.environ.get("GITHUB_TOKEN")
    if not username or not token:
        print(
            "✖ Не заданы переменные окружения GITHUB_USERNAME и/или GITHUB_TOKEN.\n"
            "  Пример:\n"
            "    export GITHUB_USERNAME=yourname\n"
            "    export GITHUB_TOKEN=ghp_xxx_with_repo_scope\n",
            file=sys.stderr,
        )
        sys.exit(1)

    print("☁️  Создаю репозиторий на GitHub...")
    resp = requests.post(
        "https://api.github.com/user/repos",
        headers={"Authorization": f"token {token}",
                 "Accept": "application/vnd.github+json"},
        json={"name": name, "description": description, "private": bool(private)},
        timeout=30,
    )
    if resp.status_code not in (201, 202):
        print(f"✖ Не удалось создать репозиторий: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)

    repo = resp.json()
    clone_url = repo.get("clone_url")
    if not clone_url:
        print(f"✖ Не удалось получить clone_url: {repo}", file=sys.stderr)
        sys.exit(1)

    git("remote", "add", "origin", clone_url, cwd=project)
    git("push", "-u", "origin", "main", cwd=project)
    print(f"✅ Репозиторий создан: https://github.com/{username}/{name}")

def main():
    args = parse_args()
    project = Path.cwd()
    print(f"📁 Использую текущую папку как проект: {project}")

    # Проверяем наличие файлов и папок кроме venv и .git
    entries = [p for p in project.iterdir() if p.name not in ("venv", ".git")]
    if entries:
        print(f"⚠️  Внимание: текущая папка не пуста (найдены файлы/папки кроме venv и .git).", file=sys.stderr)

    create_structure(project, args.name, args.description, args.data_file)

    init_git_and_first_commit(project)

    if not args.no_remote:
        create_github_repo_and_push(project, args.name, args.description, args.private)
    else:
        print("⏭  Пропускаю создание удалённого репозитория (--no-remote).")


    print("\n🎉 Готово!")
    print(f"• Локальный проект: {project}")
    if not args.no_remote:
        print(f"• GitHub: https://github.com/{os.environ.get('GITHUB_USERNAME','<user>')}/{args.name}")
    print("\nДальше:\n"
          "  1) Активируйте окружение проекта:\n"
          r"     source venv/bin/activate  # Windows: venv\Scripts\activate.bat" "\n"
          "  2) Установите зависимости:\n"
          "     pip install -r requirements.txt\n")

if __name__ == "__main__":
    main()
