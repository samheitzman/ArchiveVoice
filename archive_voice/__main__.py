from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .gui import MainWindow
from .runtime import configure_packaged_runtime


def main() -> int:
    configure_packaged_runtime()
    app = QApplication(sys.argv)
    app.setApplicationName("Archive Voice")
    app.setOrganizationName("Archive Voice")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
