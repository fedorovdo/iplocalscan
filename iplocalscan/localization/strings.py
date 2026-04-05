from __future__ import annotations

TRANSLATIONS = {
    "en": {
        "app.title": "IP Local Scan",
        "main.network_range_label": "Network range",
        "main.network_range_placeholder": "Example: 192.168.1.0/24",
        "main.scan_button": "Scan",
        "main.stop_button": "Stop",
        "main.history_button": "History",
        "main.filter_label": "Filter",
        "main.filter_placeholder": "Search by IP, MAC, vendor, hostname, status, ports, or services",
        "history.title": "Recent Scans",
        "history.description": "The latest {limit} stored scans are listed below.",
        "history.empty": "No scan history is available yet.",
        "history.saved_scans_label": "Saved scans",
        "history.preview_label": "Results preview",
        "history.scan_item": (
            "{started_at} | {network_range} | {status} | {result_count} result(s)"
        ),
        "history.details.empty": "Select a saved scan to preview its results.",
        "history.close_button": "Close",
        "table.ip_address": "IP Address",
        "table.mac_address": "MAC Address",
        "table.vendor": "Vendor",
        "table.hostname": "Hostname",
        "table.status": "Status",
        "table.open_ports": "Open Ports",
        "table.services": "Services",
        "status.ready": "Ready.",
        "status.invalid_network": (
            "Enter an IPv4 network in CIDR format, for example {example}."
        ),
        "status.scan_started": "Starting scan for {network_range}...",
        "status.scan_progress.discovery": (
            "Discovering hosts in {network_range}: checked {completed_hosts}/{total_hosts}, "
            "found {discovered_hosts} online."
        ),
        "status.scan_progress.ports": (
            "Scanning ports for {total_hosts} host(s): completed {completed_hosts}/{total_hosts}, "
            "{hosts_with_open_ports} host(s) with open ports."
        ),
        "status.scan_completed": (
            "Scan completed for {network_range}. Found {result_count} online host(s) and finished basic port scanning."
        ),
        "status.scan_stopped": (
            "Scan stopped for {network_range}. Found {result_count} online host(s) before cancellation."
        ),
        "status.scan_failed": "Scan failed: {reason}",
        "status.scan_already_running": "A scan is already in progress.",
        "status.no_active_scan": "There is no active scan to stop.",
        "status.stop_requested": "Stopping scan...",
        "status.host.unknown": "Unknown",
        "status.host.up": "Online",
        "status.host.down": "Offline",
        "status.scan.pending": "Pending",
        "status.scan.running": "Running",
        "status.scan.completed": "Completed",
        "status.scan.stopped": "Stopped",
        "status.scan.failed": "Failed",
        "scan.note.completed": "Host discovery and basic port scanning completed.",
        "scan.note.stop_requested": "The scan was stopped by the user.",
        "common.not_available": "N/A",
    },
    "ru": {
        "app.title": "IP Local Scan",
        "main.network_range_label": "Диапазон сети",
        "main.network_range_placeholder": "Пример: 192.168.1.0/24",
        "main.scan_button": "Сканировать",
        "main.stop_button": "Стоп",
        "main.history_button": "История",
        "main.filter_label": "Фильтр",
        "main.filter_placeholder": "Поиск по IP, MAC, производителю, имени хоста, статусу, портам или сервисам",
        "history.title": "Последние сканирования",
        "history.description": "Ниже показаны последние {limit} сохраненных сканирования.",
        "history.empty": "История сканирований пока пуста.",
        "history.saved_scans_label": "Сохраненные сканирования",
        "history.preview_label": "Предпросмотр результатов",
        "history.scan_item": (
            "{started_at} | {network_range} | {status} | {result_count} результат(ов)"
        ),
        "history.details.empty": "Выберите сохраненное сканирование для просмотра результатов.",
        "history.close_button": "Закрыть",
        "table.ip_address": "IP-адрес",
        "table.mac_address": "MAC-адрес",
        "table.vendor": "Производитель",
        "table.hostname": "Имя хоста",
        "table.status": "Статус",
        "table.open_ports": "Открытые порты",
        "table.services": "Сервисы",
        "status.ready": "Готово.",
        "status.invalid_network": (
            "Введите IPv4-сеть в формате CIDR, например {example}."
        ),
        "status.scan_started": "Запуск сканирования для {network_range}...",
        "status.scan_progress.discovery": (
            "Поиск хостов в {network_range}: проверено {completed_hosts}/{total_hosts}, "
            "найдено в сети {discovered_hosts}."
        ),
        "status.scan_progress.ports": (
            "Сканирование портов для {total_hosts} хостов: завершено {completed_hosts}/{total_hosts}, "
            "хостов с открытыми портами: {hosts_with_open_ports}."
        ),
        "status.scan_completed": (
            "Сканирование {network_range} завершено. Найдено {result_count} узлов в сети, базовое сканирование портов завершено."
        ),
        "status.scan_stopped": (
            "Сканирование {network_range} остановлено. До отмены найдено {result_count} узлов в сети."
        ),
        "status.scan_failed": "Ошибка сканирования: {reason}",
        "status.scan_already_running": "Сканирование уже выполняется.",
        "status.no_active_scan": "Нет активного сканирования для остановки.",
        "status.stop_requested": "Остановка сканирования...",
        "status.host.unknown": "Неизвестно",
        "status.host.up": "В сети",
        "status.host.down": "Не в сети",
        "status.scan.pending": "Ожидание",
        "status.scan.running": "Выполняется",
        "status.scan.completed": "Завершено",
        "status.scan.stopped": "Остановлено",
        "status.scan.failed": "Ошибка",
        "scan.note.completed": "Обнаружение хостов и базовое сканирование портов завершены.",
        "scan.note.stop_requested": "Сканирование остановлено пользователем.",
        "common.not_available": "Н/Д",
    },
}
